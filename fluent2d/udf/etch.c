/* TMAH etching of poly-Si in a high-aspect-ratio slit: Fluent 2024 R1 compiled UDF.
 *
 * User-defined scalars, phi_i = c_i / RHO (so rho*phi = c in mol/m3):
 *   UDS 0  OH-              z = -1
 *   UDS 1  SiO2(OH)2^2-     z = -2   (silicate)
 *   UDS 2  H2 (dissolved)   z =  0
 *   TMA+ (z = +1) is not solved: electroneutrality gives c_TMA = c_OH + 2 c_SIL.
 *
 * Transport (same equations as etchsim/slit1d.py; docs/formulation.md):
 *   N_i = c_i u - (D_i + D_osc) grad c_i + z_i D_i c_i (S/Q)
 *   S = sum_j z_j D_j grad c_j,  Q = sum_j z_j^2 D_j c_j   (j = OH, SIL, TMA)
 * The last term is electromigration in the diffusion potential (zero current + electroneutrality).
 * face_source adds it (and the D_osc mixing) as a conservative cell source; Fluent 24.1 attached neither
 * the UDS flux hook nor a per-UDS diffusivity UDF. S.A is evaluated on each face from the two cell values
 * ((c1 - c0) A.A / A.dr, exact for this orthogonal Cartesian mesh), identically from both sides.
 *
 * Reaction on poly-Si faces (zone POLY_ID) as a source in the wall-adjacent cell:
 *   Si + 2 OH- + 2 H2O -> SiO2(OH)2^2- + 2 H2,   r = K_SI (c/CB)^ORDER c/(c + EPS CB)  [mol Si/m2/s]
 *   source_i = nu_i r (poly face length / cell area),  nu = (-2, +1, +2)
 *
 * Megasonic mixing: while the oscillating flow runs, accumulate_now (called after every time step by
 * run_case.py) sums u, v, u^2, v^2; finish_avg sets D_osc = OSC_SCALE (var_u + var_v) / OMEGA_AC, i.e. |u1|^2 / (2 omega) for a
 * sinusoidal oscillation (upper bound of oscillatory dispersion), used afterwards in face_source (interior + exterior cells, so both sides of a partition agree).
 *
 * UDM: 0 poly length/cell area  1-4 sums u, v, uu, vv  5 D_osc  6 mean speed  7 etch rate [m/s]  8 samples
 *      9 sum over adjacent H2-plug faces of |A| / (distance x cell volume)  [1/m2]
 *
 * H2 plug (wall zone BUBBLE_ID): OH- and silicate cannot cross it; dissolved H2 passes into the gas, so the
 * liquid at the meniscus is held at C_H2_BUB = H2_SAT p_gas / p_atm (Henry's law at the plug pressure).
 * Added as the cell source -D_H2 (c - C_H2_BUB) |A| / (d V) in the adjacent cells; the plug keeps its size.
 */
#include "udf.h"
#include "etch_params.h"

#define UDM_AV 0
#define UDM_SU 1
#define UDM_SV 2
#define UDM_SUU 3
#define UDM_SVV 4
#define UDM_DOSC 5
#define UDM_UMEAN 6
#define UDM_RATE 7
#define UDM_N 8
#define UDM_BUB 9

#if !RP_HOST
static int accumulating = 0;
#endif

/* prints once per compute process and scalar the first time Fluent calls a hooked function, so the job
   log shows which TUI/settings hookups actually took effect */
static void hook_seen(const char *name, int i)
{
    static int seen[4][3];
    int k = name[0] == 'f' ? 0 : name[0] == 'd' ? 1 : 2;
    if (i < 0 || i > 2 || seen[k][i])
        return;
    seen[k][i] = 1;
    Message("HOOK %s uds-%d active on node %d\n", name, i, myid);
}

static real rate_si(real c_oh)
{
    real c = MAX(c_oh, 0.0);
    return K_SI * pow(c / CB, ORDER) * c / (c + EPS * CB);
}

static real drate_si(real c_oh)
{
    real c = MAX(c_oh, 1e-12 * CB);
    real p = pow(c / CB, ORDER), e = EPS * CB;
    return K_SI * (ORDER / c * p * c / (c + e) + p * e / ((c + e) * (c + e)));
}

static real cell_c(cell_t c, Thread *t, int i) { return RHO * C_UDSI(c, t, i); }

/* Fluent calls property/flux/source hooks as soon as they are attached, before initialisation has
   allocated UDM/UDS storage; reading it then kills the compute process (seen on Puma 2026-10-30) */
#define HAS_UDM(t) NNULLP(THREAD_STORAGE(t, SV_UDM_I))
#define HAS_UDS(t) (NNULLP(THREAD_STORAGE(t, SV_UDS_I(0))) && NNULLP(THREAD_STORAGE(t, SV_UDS_I(1))))

#if !RP_HOST
static void zero_udm(Domain *d, int first, int last)
{
    Thread *t;
    cell_t c;
    int k;
    thread_loop_c(t, d)
    {
        begin_c_loop_all(c, t)
        {
            for (k = first; k <= last; k++)
                C_UDMI(c, t, k) = 0.0;
        }
        end_c_loop_all(c, t)
    }
}
#endif

/* poly-Si wall length per cell area for every wall-adjacent cell; run once after initialisation */
DEFINE_ON_DEMAND(init_poly_area)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *tp = Lookup_Thread(d, POLY_ID);
    face_t f;
    real A[ND_ND], len = 0.0;
    int n = 0;
    Thread *tf;
    int nb = 0;
    zero_udm(d, UDM_AV, UDM_AV);
    zero_udm(d, UDM_BUB, UDM_BUB);
    thread_loop_f(tf, d)                                      /* H2 plug menisci, if this case has a plug */
    {
        if ((THREAD_ID(tf) != BUBBLE_ID && THREAD_ID(tf) != BUBBLE_POCKET_ID) || !BOUNDARY_FACE_THREAD_P(tf)
            || BUB_TOP <= 0.0)          /* Fluent may give an interior zone (e.g. slit-bulk faces) id 12 or 13 in
                                           meshes without a plug; 13 = pocket mouths beside a plug (comb walls) */
            continue;
        begin_f_loop(f, tf)
        {
            if (PRINCIPAL_FACE_P(f, tf))
            {
                cell_t c0 = F_C0(f, tf);
                Thread *t0 = THREAD_T0(tf);
                real xf[ND_ND], xc[ND_ND], dx[ND_ND], dist;
                F_AREA(A, f, tf);
                F_CENTROID(xf, f, tf);
                C_CENTROID(xc, c0, t0);
                NV_VV(dx, =, xf, -, xc);
                dist = fabs(NV_DOT(dx, A)) / NV_MAG(A);
                C_UDMI(c0, t0, UDM_BUB) += NV_MAG(A) / (dist * C_VOLUME(c0, t0));
                nb++;
            }
        }
        end_f_loop(f, tf)
    }
    nb = PRF_GISUM1(nb);
    Message0("init_poly_area: %d H2-plug faces (held at %g mol/m3 H2)\n", nb, C_H2_BUB);
    begin_f_loop(f, tp)
    {
        if (PRINCIPAL_FACE_P(f, tp))
        {
            cell_t c0 = F_C0(f, tp);
            Thread *t0 = THREAD_T0(tp);
            F_AREA(A, f, tp);
            C_UDMI(c0, t0, UDM_AV) += NV_MAG(A) / C_VOLUME(c0, t0);
            len += NV_MAG(A);
            n++;
        }
    }
    end_f_loop(f, tp)
    len = PRF_GRSUM1(len);
    n = PRF_GISUM1(n);
    Message0("init_poly_area: %d poly-Si faces, total length %g m (expected %g m)\n", n, len, POLY_LENGTH);
#endif
}

DEFINE_ON_DEMAND(start_avg)
{
#if !RP_HOST
    zero_udm(Get_Domain(1), UDM_SU, UDM_SVV);
    zero_udm(Get_Domain(1), UDM_N, UDM_N);
    accumulating = 1;
    Message0("start_avg: accumulating velocity statistics\n");
#endif
}

DEFINE_ON_DEMAND(finish_avg)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    real dmax = 0.0, umax = 0.0;
    accumulating = 0;
    thread_loop_c(t, d)
    {
        begin_c_loop_all(c, t)
        {
            real n = C_UDMI(c, t, UDM_N);
            if (n > 0.5)
            {
                real mu = C_UDMI(c, t, UDM_SU) / n, mv = C_UDMI(c, t, UDM_SV) / n;
                real vu = MAX(C_UDMI(c, t, UDM_SUU) / n - mu * mu, 0.0);
                real vv = MAX(C_UDMI(c, t, UDM_SVV) / n - mv * mv, 0.0);
                C_UDMI(c, t, UDM_DOSC) = OSC_SCALE * (vu + vv) / OMEGA_AC;
                C_UDMI(c, t, UDM_UMEAN) = sqrt(mu * mu + mv * mv);
                dmax = MAX(dmax, C_UDMI(c, t, UDM_DOSC));
                umax = MAX(umax, C_UDMI(c, t, UDM_UMEAN));
            }
        }
        end_c_loop_all(c, t)
    }
    dmax = PRF_GRHIGH1(dmax);
    umax = PRF_GRHIGH1(umax);
    Message0("REPORT_OSC D_osc_max %g mean_speed_max %g D_OH %g\n", dmax, umax, D_OH);
#endif
}

/* called by run_case.py after every time step of the averaging window (no function hook needed) */
DEFINE_ON_DEMAND(accumulate_now)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    if (!accumulating)
        return;
    thread_loop_c(t, d)
    {
        begin_c_loop_all(c, t)
        {
            real u = C_U(c, t), v = C_V(c, t);
            C_UDMI(c, t, UDM_SU) += u;
            C_UDMI(c, t, UDM_SV) += v;
            C_UDMI(c, t, UDM_SUU) += u * u;
            C_UDMI(c, t, UDM_SVV) += v * v;
            C_UDMI(c, t, UDM_N) += 1.0;
        }
        end_c_loop_all(c, t)
    }
#endif
}

/* plain convection for every scalar. Electromigration is NOT here: the 24.1 UDS TUI never attached this
 * hook (no "HOOK flux" on Puma 2026-10-30), so it lives in face_source. If the hook ever does attach,
 * returning F_FLUX keeps it identical to Fluent's default and nothing is counted twice. */
DEFINE_UDS_FLUX(uds_flux, f, t, i)
{
    hook_seen("flux", i);
    return NNULLP(THREAD_STORAGE(t, SV_FLUX)) ? F_FLUX(f, t) : 0.0;
}

/* Face-flux terms that Fluent 24.1 cannot take through its settings API, added as a cell source:
 *  (a) megasonic mixing div(rho D_osc grad phi_i): flux k_f (phi_nb - phi_c), k_f = rho D_osc,f A.A/|A.dr|,
 *      D_osc,f = mean of the two cells (the per-UDS user-defined diffusivity field is inactive in 24.1),
 *      plus the molecular remainder D_i - D_BASE: 24.1 applies ONE constant diffusivity to all UDS (M0_none
 *      2026-10-30: all three diffused with D_H2), so every UDS gets rho D_BASE in Fluent, D_BASE = the LARGEST
 *      D (OH-), and the remainder (<= 0) is a deferred correction here: lagged neighbours, converging by a
 *      factor |D_i - D_BASE|/D_BASE (0.83 silicate, 0.15 H2) per iteration. A positive remainder with
 *      D_BASE = smallest D froze OH- and H2 (explicit neighbours dominate -> Jacobi, ~N^2 iterations);
 *      plus, above a pulsating H2 plug, the pumping dispersion D_pump,i (etchsim/cavitation.py, Taylor-Aris
 *      of the oscillating column) on the axial (horizontal) faces of the slit only;
 *  (b) electromigration, ions only: outward flux J = z_i D_i c_f (S.A_out)/Q_f [mol/s per m depth],
 *      S.A_out = sum_j z_j D_j (c_j,nb - c_j,c) A.A/|A.dr|, Q_f = sum_j z_j^2 D_j c_j,f,
 *      c_f = mean of the two cells (central; migration is diffusion-like, cell Peclet << 1).
 * Each face is computed identically from both sides, so the scheme is conservative across zones and
 * partitions (exterior-cell UDS values are synced by Fluent; D_osc is set in exterior cells too).
 * Exact on this orthogonal Cartesian mesh. Interior faces only: ASSUMED no mixing or migration flux through
 * inlet/outlet/top (far from the slit, uniform specified values) and none through walls. */
/* slit liquid between the mouth and the top of the H2 plug, where the pulsating bubble pumps (BUB_TOP = 0: none) */
static int in_pump(const real *x)
{
    return BUB_TOP > 0.0 && x[0] > 0.0 && x[0] < W_SLIT && x[1] < 0.0 && x[1] > -BUB_TOP;
}

static real face_source(cell_t c, Thread *t, int i, real *dsdphi)
{
    int n;
    real s = 0.0, diag = 0.0, dc = C_UDMI(c, t, UDM_DOSC), xc[ND_ND];
    real zi = (i == 0) ? -1.0 : (i == 1) ? -2.0 : 0.0;
    real Di = (i == 0) ? D_OH : (i == 1) ? D_SIL : D_H2;
    real dm = Di - D_BASE;                                    /* molecular D not carried by Fluent */
    real dp = (i == 0) ? DPUMP_OH : (i == 1) ? DPUMP_SIL : DPUMP_H2;  /* bubble pumping (axial faces) */
    real coh = cell_c(c, t, 0), csi = cell_c(c, t, 1), ci = cell_c(c, t, i);
    int migrate = MIGRATION && zi != 0.0;
    C_CENTROID(xc, c, t);
    c_face_loop(c, t, n)
    {
        face_t f = C_FACE(c, t, n);
        Thread *tf = C_FACE_THREAD(c, t, n);
        cell_t cn;
        Thread *tn;
        real A[ND_ND], xn[ND_ND], dr[ND_ND], dn, geo, k, pf;
        int pface;
        if (BOUNDARY_FACE_THREAD_P(tf))
            continue;
        if (F_C0(f, tf) == c && THREAD_T0(tf) == t) { cn = F_C1(f, tf); tn = THREAD_T1(tf); }
        else { cn = F_C0(f, tf); tn = THREAD_T0(tf); }
        if (!HAS_UDM(tn) || !HAS_UDS(tn))
            continue;
        F_AREA(A, f, tf);
        C_CENTROID(xn, cn, tn);
        NV_VV(dr, =, xn, -, xc);
        geo = NV_DOT(A, A) / fabs(NV_DOT(A, dr));             /* grad c . A_out = (c_nb - c_c) geo */
        dn = C_UDMI(cn, tn, UDM_DOSC);
        pface = BUB_TOP > 0.0 && fabs(A[1]) > fabs(A[0]) && in_pump(xc) && in_pump(xn);
        pf = pface ? dp : 0.0;
        if (dc > 0.0 || dn > 0.0 || dm != 0.0 || pf > 0.0)   /* (a) mixing + molecular remainder + pumping */
        {
            k = RHO * (0.5 * (dc + dn) + dm + pf) * geo;
            s += k * (C_UDSI(cn, tn, i) - C_UDSI(c, t, i));
            if (k > 0.0)
                diag -= k;                                    /* implicit part only where it stabilises */
        }
        if (migrate)                                          /* (b) electromigration */
        {
            real ohn = cell_c(cn, tn, 0), sin_ = cell_c(cn, tn, 1);
            real d_oh = (ohn - coh) * geo, d_si = (sin_ - csi) * geo;
            /* zero current includes the pumping dispersion of every ion (it moves charge too) */
            real p_oh = pface ? DPUMP_OH : 0.0, p_si = pface ? DPUMP_SIL : 0.0, p_tma = pface ? DPUMP_TMA : 0.0;
            real s_a = -(D_OH + p_oh) * d_oh - 2.0 * (D_SIL + p_si) * d_si + (D_TMA + p_tma) * (d_oh + 2.0 * d_si);
            real co = 0.5 * (coh + ohn), cs = 0.5 * (csi + sin_);
            real q = D_OH * MAX(co, 0.0) + 4.0 * D_SIL * MAX(cs, 0.0) + D_TMA * MAX(co + 2.0 * cs, 0.0);
            real cf = 0.5 * (ci + cell_c(cn, tn, i));
            real w;
            q = MAX(q, 1e-9 * CB * D_TMA);
            w = zi * Di * s_a / q;                            /* outward drift "conductance" [m2/s per m] */
            s -= w * cf;
            if (w > 0.0)
                diag -= 0.5 * w * RHO;                        /* d(-w c_f)/d phi_c, kept only if stabilising */
        }
    }
    *dsdphi = diag / C_VOLUME(c, t);
    return s / C_VOLUME(c, t);
}

/* i: UDS index; nu: stoichiometric coefficient per Si (OH- -2, silicate +1, H2 +2) */
static real src(cell_t c, Thread *t, int i, real nu, real dS[], int eqn, int implicit)
{
    real av, c_oh, s_mix, ds_mix;
    hook_seen("source", i);
    if (!HAS_UDM(t) || !HAS_UDS(t))                          /* called before initialisation */
    {
        dS[eqn] = 0.0;
        return 0.0;
    }
    s_mix = face_source(c, t, i, &ds_mix);
    if (i == 2 && C_UDMI(c, t, UDM_BUB) > 0.0)               /* H2 into the adjacent gas plug */
    {
        real kb = D_H2 * C_UDMI(c, t, UDM_BUB);
        s_mix -= kb * (cell_c(c, t, 2) - C_H2_BUB);
        ds_mix -= kb * RHO;
    }
    av = C_UDMI(c, t, UDM_AV);
    if (av <= 0.0)
    {
        dS[eqn] = ds_mix;
        return s_mix;
    }
    c_oh = cell_c(c, t, 0);
    dS[eqn] = ds_mix + (implicit ? nu * av * drate_si(c_oh) * RHO : 0.0);   /* dS/dphi, phi = c / rho */
    return s_mix + nu * av * rate_si(c_oh);                       /* mol/m3/s = rho phi per second */
}

/* bodies on their own lines: Fluent's udf_names.c generator copies the rest of the macro line verbatim */
DEFINE_SOURCE(src_oh, c, t, dS, eqn)
{
    return src(c, t, 0, -2.0, dS, eqn, 1);
}

DEFINE_SOURCE(src_sil, c, t, dS, eqn)
{
    return src(c, t, 1, 1.0, dS, eqn, 0);
}

DEFINE_SOURCE(src_h2, c, t, dS, eqn)
{
    return src(c, t, 2, 2.0, dS, eqn, 0);
}

/* every compute process writes its own cells: poly-Si wall cells and the slit/mouth centre column.
   File dump_<id>.csv in the working directory; run_case.py concatenates them (no Fluent export needed). */
DEFINE_ON_DEMAND(dump)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    char name[64];
    FILE *fp;
    real x[ND_ND];
#if PARALLEL
    int id = myid;
#else
    int id = 0;
#endif
    sprintf(name, "dump_%d.csv", id);
    fp = fopen(name, "w");
    if (fp == NULL)
        return;
    fprintf(fp, "kind,x,y,c_oh,c_sil,c_h2,d_osc,u_mean,etch_m_s,area_per_vol\n");
    thread_loop_c(t, d)
    {
        begin_c_loop_int(c, t)
        {
            int poly = C_UDMI(c, t, UDM_AV) > 0.0;
            C_CENTROID(x, c, t);
            if (poly || fabs(x[0] - 0.5 * W_SLIT) < DX_CELL)      /* the two columns either side of the centre */
            {
                real co = cell_c(c, t, 0);
                fprintf(fp, "%s,%.9e,%.9e,%.9e,%.9e,%.9e,%.6e,%.6e,%.6e,%.6e\n", poly ? "poly" : "centre",
                        x[0], x[1], co, cell_c(c, t, 1), cell_c(c, t, 2), C_UDMI(c, t, UDM_DOSC),
                        C_UDMI(c, t, UDM_UMEAN), poly ? rate_si(co) * M_SI / RHO_SI : 0.0, C_UDMI(c, t, UDM_AV));
            }
        }
        end_c_loop_int(c, t)
    }
    fclose(fp);
#endif
}

/* Whole-field snapshot for contour plots (make_contours.py): every interior cell of this process to
   field_<id>.csv with concentrations, the instantaneous velocity, D_osc, the phase-A mean speed and the
   local etch rate (poly-Si wall cells only). */
DEFINE_ON_DEMAND(dump_field)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    char name[64];
    FILE *fp;
    real x[ND_ND];
#if PARALLEL
    int id = myid;
#else
    int id = 0;
#endif
    sprintf(name, "field_%d.csv", id);
    fp = fopen(name, "w");
    if (fp == NULL)
        return;
    fprintf(fp, "x,y,c_oh,c_sil,c_h2,u,v,d_osc,u_mean,etch_m_s\n");
    thread_loop_c(t, d)
    {
        if (!HAS_UDM(t) || !HAS_UDS(t))
            continue;
        begin_c_loop_int(c, t)
        {
            real co = cell_c(c, t, 0);
            int poly = C_UDMI(c, t, UDM_AV) > 0.0;
            C_CENTROID(x, c, t);
            fprintf(fp, "%.9e,%.9e,%.9e,%.9e,%.9e,%.6e,%.6e,%.6e,%.6e,%.6e\n", x[0], x[1], co, cell_c(c, t, 1),
                    cell_c(c, t, 2), C_U(c, t), C_V(c, t), C_UDMI(c, t, UDM_DOSC), C_UDMI(c, t, UDM_UMEAN),
                    poly ? rate_si(co) * M_SI / RHO_SI : 0.0);
        }
        end_c_loop_int(c, t)
    }
    fclose(fp);
#endif
}

/* etch rate into UDM 7 and a one-line summary */
DEFINE_ON_DEMAND(report)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    real cmin = 1e30, cmax = -1e30, smax = 0.0, h2max = 0.0, rmax = 0.0, rmin = 1e30;
    real h2_in = 0.0;                                         /* H2 into a gas plug [mol/s per m] */
    thread_loop_c(t, d)
    {
        begin_c_loop_int(c, t)
        {
            real co = cell_c(c, t, 0);
            cmin = MIN(cmin, co);
            cmax = MAX(cmax, co);
            smax = MAX(smax, cell_c(c, t, 1));
            h2max = MAX(h2max, cell_c(c, t, 2));
            if (C_UDMI(c, t, UDM_BUB) > 0.0)
                h2_in += D_H2 * C_UDMI(c, t, UDM_BUB) * (cell_c(c, t, 2) - C_H2_BUB) * C_VOLUME(c, t);
            if (C_UDMI(c, t, UDM_AV) > 0.0)
            {
                real r = rate_si(co) * M_SI / RHO_SI;
                C_UDMI(c, t, UDM_RATE) = r;
                rmax = MAX(rmax, r);
                rmin = MIN(rmin, r);
            }
        }
        end_c_loop_int(c, t)
    }
    cmin = PRF_GRLOW1(cmin); cmax = PRF_GRHIGH1(cmax); smax = PRF_GRHIGH1(smax);
    h2max = PRF_GRHIGH1(h2max); rmax = PRF_GRHIGH1(rmax); rmin = PRF_GRLOW1(rmin);
    Message0("REPORT c_OH_min %g c_OH_max %g c_SIL_max %g c_H2_max %g etch_min_nm_min %g etch_max_nm_min %g\n",
             cmin, cmax, smax, h2max, rmin * 6e10, rmax * 6e10);
    h2_in = PRF_GRSUM1(h2_in);
    if (BUB_TOP > 0.0)                                        /* plug lengthens at h2_in / (gas density x W) */
        Message0("PLUG H2_in %g mol/s/m growth %g um/s\n", h2_in, h2_in / (RHO_GAS_PLUG * W_SLIT) * 1e6);
#endif
}
