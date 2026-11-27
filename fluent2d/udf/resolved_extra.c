/* ---------------------------------------------------------------------------------------------------------
 * Case 10, RESOLVED oscillation (appended to etch.c by run_resolved.py; no D_osc closure).
 *
 * The megasonic field is not turned into a mixing coefficient. The species are carried by the actual
 * oscillating velocity that Fluent solves every time step (40 steps per acoustic period).
 *
 * Driving (wafer frame, x along the wafer, y up; the cell is << the wavelength, so the wave is uniform in it):
 *   tangential:  body force  S_x = RHO U_T OMEGA cos(OMEGA (t - t0))  in every liquid cell. Far from the wafer the
 *                liquid then slides as U_T sin(OMEGA (t - t0)); the no-slip wafer makes the Stokes layer itself.
 *   normal (pressure antinode, compression): the liquid is compressed by p(t) = P_WALL sin(OMEGA (t - t0)),
 *                which is a mass source  S_m = -(1/c^2) dp/dt = -(OMEGA P_WALL / c^2) cos(OMEGA (t - t0))  in every
 *                liquid cell (linear acoustics; p is uniform over the cell because lambda = 1.55 mm). The same mass
 *                leaves through the top (velocity inlet v_top, set by run_resolved.py from the meshed liquid area).
 * SOUND_ON is switched by the on-demand functions sound_on / sound_off; t0 is the time of sound_on.
 *
 * Measurement (acc_rows, called by run_resolved.py every STEPS_PER_SAMPLE steps): for every cell, the H2 flux
 * through its TOP face, split into convection (Fluent's face mass flux / RHO x face-average c) and diffusion
 * (-D_H2 dc/dy x face length), and dc/dy x face length; also the cell's c_H2 and the velocity statistics used by
 * the old closure (UDM 1-4, 8), so finish_avg can still compute the closure D_osc for comparison.
 * Per horizontal row of faces (post-processing):  D_eff(y) = -(sum J) / (sum dc/dy x length)  -- the mixing the
 * resolved flow really produces at that height. Pure diffusion gives D_eff = D_H2 exactly.
 * --------------------------------------------------------------------------------------------------------- */
#define UDM_RJC 10   /* sum of convective H2 flux through the top face [mol/s per m depth] */
#define UDM_RJD 11   /* sum of diffusive H2 flux through the top face */
#define UDM_RG 12    /* sum of dc/dy x face length [mol/m3] */
#define UDM_RC 13    /* sum of c_H2 [mol/m3] */
#define UDM_RN 14    /* number of samples */
#define UDM_RLEN 15  /* top-face length [m] (0 = no interior top face) */
#define UDM_RYF 16   /* top-face y [m] */
#define UDM_RSH 17   /* sum of the shear du/dy at the top face [1/s] */
#define UDM_RSH2 18  /* sum of its square */
#define N_UDM_RESOLVED 19

#if !RP_HOST
static int sound_flag = 0;
static real t_zero = 0.0;
#endif

DEFINE_ON_DEMAND(sound_on)
{
#if !RP_HOST
    sound_flag = 1;
    t_zero = CURRENT_TIME;
    Message0("sound_on at t0 = %.12g s (U_T %g m/s, P_WALL %g Pa)\n", t_zero, U_T, P_WALL);
#endif
}

DEFINE_ON_DEMAND(sound_off)
{
#if !RP_HOST
    sound_flag = 0;
#endif
}

DEFINE_SOURCE(xmom_src, c, t, dS, eqn)
{
    dS[eqn] = 0.0;
#if !RP_HOST
    if (sound_flag)
        return RHO * U_T * OMEGA_AC * cos(OMEGA_AC * (CURRENT_TIME - t_zero));
#endif
    return 0.0;
}

DEFINE_SOURCE(mass_src, c, t, dS, eqn)
{
    dS[eqn] = 0.0;
#if !RP_HOST
    if (sound_flag)
        return -OMEGA_AC * P_WALL / (C_SOUND_L * C_SOUND_L) * cos(OMEGA_AC * (CURRENT_TIME - t_zero));
#endif
    return 0.0;
}

#if !RP_HOST
/* the face above cell c (outward normal +y), or -1 */
static int top_face(cell_t c, Thread *t, face_t *fo, Thread **to)
{
    int n;
    real xc[ND_ND];
    C_CENTROID(xc, c, t);
    c_face_loop(c, t, n)
    {
        face_t f = C_FACE(c, t, n);
        Thread *tf = C_FACE_THREAD(c, t, n);
        real A[ND_ND], xf[ND_ND];
        F_AREA(A, f, tf);
        F_CENTROID(xf, f, tf);
        if (fabs(A[1]) > 10.0 * fabs(A[0]) && xf[1] > xc[1])
        {
            *fo = f;
            *to = tf;
            return n;
        }
    }
    return -1;
}
#endif

DEFINE_ON_DEMAND(start_rows)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    zero_udm(d, UDM_RJC, UDM_RSH2);
    zero_udm(d, UDM_SU, UDM_SVV);
    zero_udm(d, UDM_N, UDM_N);
    Message0("start_rows: accumulating H2 fluxes per row and velocity statistics\n");
#endif
}

DEFINE_ON_DEMAND(acc_rows)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    thread_loop_c(t, d)
    {
        if (!HAS_UDM(t) || !HAS_UDS(t))
            continue;
        begin_c_loop_int(c, t)
        {
            face_t f;
            Thread *tf;
            real u = C_U(c, t), v = C_V(c, t), ci = cell_c(c, t, 2);
            C_UDMI(c, t, UDM_SU) += u;                       /* closure statistics, as accumulate_now */
            C_UDMI(c, t, UDM_SV) += v;
            C_UDMI(c, t, UDM_SUU) += u * u;
            C_UDMI(c, t, UDM_SVV) += v * v;
            C_UDMI(c, t, UDM_N) += 1.0;
            C_UDMI(c, t, UDM_RC) += ci;
            C_UDMI(c, t, UDM_RN) += 1.0;
            if (top_face(c, t, &f, &tf) >= 0 && !BOUNDARY_FACE_THREAD_P(tf))
            {
                cell_t cn;
                Thread *tn;
                real A[ND_ND], xc[ND_ND], xn[ND_ND], xf[ND_ND], len, dy, cnv, q, mflux;
                int is0 = (F_C0(f, tf) == c && THREAD_T0(tf) == t);
                if (is0) { cn = F_C1(f, tf); tn = THREAD_T1(tf); }
                else { cn = F_C0(f, tf); tn = THREAD_T0(tf); }
                if (!HAS_UDS(tn))
                    continue;
                F_AREA(A, f, tf);
                F_CENTROID(xf, f, tf);
                C_CENTROID(xc, c, t);
                C_CENTROID(xn, cn, tn);
                len = NV_MAG(A);
                dy = xn[1] - xc[1];
                cnv = cell_c(cn, tn, 2);
                mflux = NNULLP(THREAD_STORAGE(tf, SV_FLUX)) ? F_FLUX(f, tf) : 0.0;   /* kg/s per m, c0 -> c1 */
                q = (is0 ? mflux : -mflux) / RHO;                                   /* upward volume flux */
                C_UDMI(c, t, UDM_RJC) += q * 0.5 * (ci + cnv);
                C_UDMI(c, t, UDM_RJD) += -D_H2 * (cnv - ci) / dy * len;
                C_UDMI(c, t, UDM_RG) += (cnv - ci) / dy * len;
                C_UDMI(c, t, UDM_RLEN) = len;
                C_UDMI(c, t, UDM_RYF) = xf[1];
                {
                    real sh = (C_U(cn, tn) - u) / dy;          /* shear the flow itself makes */
                    C_UDMI(c, t, UDM_RSH) += sh;
                    C_UDMI(c, t, UDM_RSH2) += sh * sh;
                }
            }
        }
        end_c_loop_int(c, t)
    }
#endif
}

/* rows_<id>.csv: per cell, the time-averaged top-face fluxes, c_H2, and the closure D_osc (UDM 5, after finish_avg) */
DEFINE_ON_DEMAND(dump_rows)
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
    sprintf(name, "rows_%d.csv", id);
    fp = fopen(name, "w");
    if (fp == NULL)
        return;
    fprintf(fp, "zone,x,y,dx,y_face,len,jc,jd,grad,c_h2,n,d_osc,u_amp,shear_mean,shear_amp\n");
    thread_loop_c(t, d)
    {
        if (!HAS_UDM(t) || !HAS_UDS(t))
            continue;
        begin_c_loop_int(c, t)
        {
            real n = C_UDMI(c, t, UDM_RN), dxc = 0.0;
            int k;
            real xmin = 1e30, xmax = -1e30;
            if (n < 0.5)
                continue;
            C_CENTROID(x, c, t);
            c_node_loop(c, t, k)
            {
                Node *nd = C_NODE(c, t, k);
                xmin = MIN(xmin, NODE_X(nd));
                xmax = MAX(xmax, NODE_X(nd));
            }
            dxc = xmax - xmin;
            {
                /* oscillation amplitudes from the sampled statistics (sinusoid: amplitude = sqrt(2 variance)) */
                real nu_ = MAX(C_UDMI(c, t, UDM_N), 1.0), mu_ = C_UDMI(c, t, UDM_SU) / nu_;
                real u_amp = sqrt(2.0 * MAX(C_UDMI(c, t, UDM_SUU) / nu_ - mu_ * mu_, 0.0));
                real sm = C_UDMI(c, t, UDM_RSH) / n;
                real s_amp = sqrt(2.0 * MAX(C_UDMI(c, t, UDM_RSH2) / n - sm * sm, 0.0));
                fprintf(fp, "%d,%.9e,%.9e,%.6e,%.9e,%.6e,%.9e,%.9e,%.9e,%.9e,%g,%.6e,%.6e,%.6e,%.6e\n", THREAD_ID(t),
                        x[0], x[1], dxc, C_UDMI(c, t, UDM_RYF), C_UDMI(c, t, UDM_RLEN), C_UDMI(c, t, UDM_RJC) / n,
                        C_UDMI(c, t, UDM_RJD) / n, C_UDMI(c, t, UDM_RG) / n, C_UDMI(c, t, UDM_RC) / n, n,
                        C_UDMI(c, t, UDM_DOSC), u_amp, sm, s_amp);
            }
        }
        end_c_loop_int(c, t)
    }
    fclose(fp);
#endif
}

/* mouth_<id>.csv: length-weighted sum of the INSTANTANEOUS c_H2 in the first liquid row above the wafer and at
   the slit top, so run_resolved.py can log how the mouth H2 drifts while the sound is on; plus the H2 that leaves
   through the pinned top row (integral of the pin source, mol/s per m depth) and the top row's volume-weighted
   c_H2 (must equal PIN_C_H2) */
DEFINE_ON_DEMAND(dump_mouth)
{
#if !RP_HOST
    Domain *d = Get_Domain(1);
    Thread *t;
    cell_t c;
    char name[64];
    FILE *fp;
    real x[ND_ND], s_row = 0.0, l_row = 0.0, s_slit = 0.0, n_slit = 0.0;
    real out_h2 = 0.0, s_top = 0.0, v_top_ = 0.0;     /* H2 leaving through the pinned top row; its mean c */
#if PARALLEL
    int id = myid;
#else
    int id = 0;
#endif
    thread_loop_c(t, d)
    {
        if (!HAS_UDS(t))
            continue;
        begin_c_loop_int(c, t)
        {
            C_CENTROID(x, c, t);
            if (top_cell(c, t))
            {
                real vol = C_VOLUME(c, t);
                out_h2 += TOP_PIN_K * (cell_c(c, t, 2) - PIN_C_H2) * vol;   /* mol/s per m depth */
                s_top += cell_c(c, t, 2) * vol;
                v_top_ += vol;
            }
            if (x[1] > 0.0 && x[1] < ROW1_Y)
            {
                real w = C_VOLUME(c, t);
                s_row += cell_c(c, t, 2) * w;
                l_row += w;
            }
            else if (x[1] < 0.0 && x[1] > -DY_SLIT && x[0] > 0.0 && x[0] < W_SLIT)   /* top slit row (centroid
                                                    -DY_SLIT/2; the old -ROW1_Y test missed it, review C1) */
            {
                s_slit += cell_c(c, t, 2);
                n_slit += 1.0;
            }
        }
        end_c_loop_int(c, t)
    }
    sprintf(name, "mouth_%d.csv", id);
    fp = fopen(name, "w");
    if (fp == NULL)
        return;
    fprintf(fp, "s_row,l_row,s_slit,n_slit,out_h2,s_top,v_top\n%.12e,%.12e,%.12e,%g,%.12e,%.12e,%.12e\n", s_row,
            l_row, s_slit, n_slit, out_h2, s_top, v_top_);
    fclose(fp);
#endif
}

/* the closure D_osc (UDM 5) is only for comparison: clear it so a restart from the saved case does not mix twice */
DEFINE_ON_DEMAND(clear_dosc)
{
#if !RP_HOST
    zero_udm(Get_Domain(1), UDM_DOSC, UDM_DOSC);
#endif
}
