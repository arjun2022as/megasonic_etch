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
 * uds_flux adds it to the convective mass flux of UDS 0 and 1, so Fluent upwinds it like convection.
 * S.A is evaluated on each face from the two cell values ((c1 - c0) A.A / A.dr, exact for this
 * orthogonal Cartesian mesh), so the flux is identical on both sides of a parallel partition boundary.
 *
 * Reaction on poly-Si faces (zone POLY_ID) as a source in the wall-adjacent cell:
 *   Si + 2 OH- + 2 H2O -> SiO2(OH)2^2- + 2 H2,   r = K_SI (c/CB)^ORDER c/(c + EPS CB)  [mol Si/m2/s]
 *   source_i = nu_i r (poly face length / cell area),  nu = (-2, +1, +2)
 *
 * Megasonic mixing: while the oscillating flow runs, accumulate_now (called after every time step by
 * run_case.py) sums u, v, u^2, v^2; finish_avg sets D_osc = OSC_SCALE (var_u + var_v) / OMEGA, i.e. |u1|^2 / (2 omega) for a
 * sinusoidal oscillation (upper bound of oscillatory dispersion), used afterwards in uds_diff.
 *
 * UDM: 0 poly length/cell area  1-4 sums u, v, uu, vv  5 D_osc  6 mean speed  7 etch rate [m/s]  8 samples
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

static int accumulating = 0;

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

#if !RP_HOST
static void zero_udm(Domain *d, int first, int last)
{
    Thread *t;
    cell_t c;
    int k;
    thread_loop_c(t, d)
    {
        begin_c_loop(c, t)
        {
            for (k = first; k <= last; k++)
                C_UDMI(c, t, k) = 0.0;
        }
        end_c_loop(c, t)
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
    zero_udm(d, UDM_AV, UDM_AV);
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
        begin_c_loop(c, t)
        {
            real n = C_UDMI(c, t, UDM_N);
            if (n > 0.5)
            {
                real mu = C_UDMI(c, t, UDM_SU) / n, mv = C_UDMI(c, t, UDM_SV) / n;
                real vu = MAX(C_UDMI(c, t, UDM_SUU) / n - mu * mu, 0.0);
                real vv = MAX(C_UDMI(c, t, UDM_SVV) / n - mv * mv, 0.0);
                C_UDMI(c, t, UDM_DOSC) = OSC_SCALE * (vu + vv) / OMEGA;
                C_UDMI(c, t, UDM_UMEAN) = sqrt(mu * mu + mv * mv);
                dmax = MAX(dmax, C_UDMI(c, t, UDM_DOSC));
                umax = MAX(umax, C_UDMI(c, t, UDM_UMEAN));
            }
        }
        end_c_loop(c, t)
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
        begin_c_loop(c, t)
        {
            real u = C_U(c, t), v = C_V(c, t);
            C_UDMI(c, t, UDM_SU) += u;
            C_UDMI(c, t, UDM_SV) += v;
            C_UDMI(c, t, UDM_SUU) += u * u;
            C_UDMI(c, t, UDM_SVV) += v * v;
            C_UDMI(c, t, UDM_N) += 1.0;
        }
        end_c_loop(c, t)
    }
#endif
}

/* convective mass flux + electromigration for the ions; plain convection for H2 */
DEFINE_UDS_FLUX(uds_flux, f, t, i)
{
    real flux = F_FLUX(f, t);
    real A[ND_ND], x0[ND_ND], x1[ND_ND], dr[ND_ND];
    real zi, Di, coh0, csi0, coh1, csi1, geo, d_oh, d_si, s_dot_a, co, cs, q;
    cell_t c0;
    Thread *t0;
    if (i == 0) { zi = -1.0; Di = D_OH; }
    else if (i == 1) { zi = -2.0; Di = D_SIL; }
    else return flux;
    if (!MIGRATION)
        return flux;
    if (BOUNDARY_FACE_THREAD_P(t) && THREAD_TYPE(t) == THREAD_F_WALL)
        return flux;                                         /* nothing crosses a wall */
    c0 = F_C0(f, t);
    t0 = THREAD_T0(t);
    C_CENTROID(x0, c0, t0);
    coh0 = cell_c(c0, t0, 0);
    csi0 = cell_c(c0, t0, 1);
    if (BOUNDARY_FACE_THREAD_P(t))
    {
        F_CENTROID(x1, f, t);
        coh1 = RHO * F_UDSI(f, t, 0);
        csi1 = RHO * F_UDSI(f, t, 1);
    }
    else
    {
        cell_t c1 = F_C1(f, t);
        Thread *t1 = THREAD_T1(t);
        C_CENTROID(x1, c1, t1);
        coh1 = cell_c(c1, t1, 0);
        csi1 = cell_c(c1, t1, 1);
    }
    F_AREA(A, f, t);
    NV_VV(dr, =, x1, -, x0);
    geo = NV_DOT(A, A) / NV_DOT(A, dr);                      /* grad c . A = (c1 - c0) geo */
    d_oh = (coh1 - coh0) * geo;
    d_si = (csi1 - csi0) * geo;
    s_dot_a = -D_OH * d_oh - 2.0 * D_SIL * d_si + D_TMA * (d_oh + 2.0 * d_si);
    co = 0.5 * (coh0 + coh1);
    cs = 0.5 * (csi0 + csi1);
    q = D_OH * MAX(co, 0.0) + 4.0 * D_SIL * MAX(cs, 0.0) + D_TMA * MAX(co + 2.0 * cs, 0.0);
    q = MAX(q, 1e-9 * CB * D_TMA);
    return flux + RHO * zi * Di * s_dot_a / q;               /* + rho (z D S/Q) . A */
}

DEFINE_DIFFUSIVITY(uds_diff, c, t, i)
{
    real d = (i == 0) ? D_OH : (i == 1) ? D_SIL : D_H2;
    return RHO * (d + C_UDMI(c, t, UDM_DOSC));               /* Gamma = rho D because phi = c / rho */
}

static real src(cell_t c, Thread *t, real nu, real dS[], int eqn, int implicit)
{
    real av = C_UDMI(c, t, UDM_AV), c_oh;
    if (av <= 0.0)
    {
        dS[eqn] = 0.0;
        return 0.0;
    }
    c_oh = cell_c(c, t, 0);
    dS[eqn] = implicit ? nu * av * drate_si(c_oh) * RHO : 0.0;   /* dS/dphi with phi = c / rho */
    return nu * av * rate_si(c_oh);                               /* mol/m3/s = rho phi per second */
}

/* bodies on their own lines: Fluent's udf_names.c generator copies the rest of the macro line verbatim */
DEFINE_SOURCE(src_oh, c, t, dS, eqn)
{
    return src(c, t, -2.0, dS, eqn, 1);
}

DEFINE_SOURCE(src_sil, c, t, dS, eqn)
{
    return src(c, t, 1.0, dS, eqn, 0);
}

DEFINE_SOURCE(src_h2, c, t, dS, eqn)
{
    return src(c, t, 2.0, dS, eqn, 0);
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

/* etch rate into UDM 7 and a one-line summary */
DEFINE_ON_DEMAND(report)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    real cmin = 1e30, cmax = -1e30, smax = 0.0, h2max = 0.0, rmax = 0.0, rmin = 1e30;
    thread_loop_c(t, d)
    {
        begin_c_loop_int(c, t)
        {
            real co = cell_c(c, t, 0);
            cmin = MIN(cmin, co);
            cmax = MAX(cmax, co);
            smax = MAX(smax, cell_c(c, t, 1));
            h2max = MAX(h2max, cell_c(c, t, 2));
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
#endif
}
