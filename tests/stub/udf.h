/* Minimal stand-in for Fluent's udf.h, ONLY for a local syntax/type check of etch.c (clang -fsyntax-only).
   Macro shapes follow the Fluent UDF manual; nothing here is used on the cluster. */
#include <math.h>
#include <stdio.h>
typedef double real;
typedef int cell_t;
typedef int face_t;
typedef struct thread_struct { int id; int type; struct thread_struct *t0, *t1; } Thread;
typedef struct domain_struct { int id; } Domain;
#define ND_ND 2
#define RP_HOST 0
#define PARALLEL 1
extern int myid;
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define THREAD_F_WALL 3
#define THREAD_TYPE(t) ((t)->type)
#define THREAD_T0(t) ((t)->t0)
#define THREAD_T1(t) ((t)->t1)
#define BOUNDARY_FACE_THREAD_P(t) ((t)->t1 == NULL)
#define PRINCIPAL_FACE_P(f, t) (1)
real *udmi(cell_t c, Thread *t, int i);
real *udsi(cell_t c, Thread *t, int i);
real *fudsi(face_t f, Thread *t, int i);
#define C_UDMI(c, t, i) (*udmi(c, t, i))
#define C_UDSI(c, t, i) (*udsi(c, t, i))
#define F_UDSI(f, t, i) (*fudsi(f, t, i))
real C_U(cell_t c, Thread *t);
real C_V(cell_t c, Thread *t);
real C_VOLUME(cell_t c, Thread *t);
real F_FLUX(face_t f, Thread *t);
cell_t F_C0(face_t f, Thread *t);
cell_t F_C1(face_t f, Thread *t);
void area(real *A, face_t f, Thread *t);
void ccen(real *x, cell_t c, Thread *t);
void fcen(real *x, face_t f, Thread *t);
#define F_AREA(A, f, t) area(A, f, t)
#define C_CENTROID(x, c, t) ccen(x, c, t)
#define F_CENTROID(x, f, t) fcen(x, f, t)
#define NV_MAG(v) sqrt((v)[0] * (v)[0] + (v)[1] * (v)[1])
#define NV_DOT(a, b) ((a)[0] * (b)[0] + (a)[1] * (b)[1])
#define NV_VV(a, eq, b, op, c) ((a)[0] eq (b)[0] op (c)[0], (a)[1] eq (b)[1] op (c)[1])
Domain *Get_Domain(int i);
Thread *Lookup_Thread(Domain *d, int id);
Thread *next_c_thread(Domain *d, Thread *t);
#define thread_loop_c(t, d) for (t = next_c_thread(d, NULL); t != NULL; t = next_c_thread(d, t))
#define begin_c_loop(c, t) for (c = 0; c < 10; c++)
#define end_c_loop(c, t)
#define begin_c_loop_int(c, t) for (c = 0; c < 10; c++)
#define end_c_loop_int(c, t)
#define begin_f_loop(f, t) for (f = 0; f < 10; f++)
#define end_f_loop(f, t)
real PRF_GRSUM1(real x);
int PRF_GISUM1(int x);
real PRF_GRHIGH1(real x);
real PRF_GRLOW1(real x);
void Message0(const char *fmt, ...);
#define DEFINE_ON_DEMAND(name) void name(void)
#define DEFINE_UDS_FLUX(name, f, t, i) real name(face_t f, Thread *t, int i)
#define DEFINE_DIFFUSIVITY(name, c, t, i) real name(cell_t c, Thread *t, int i)
#define DEFINE_SOURCE(name, c, t, dS, eqn) real name(cell_t c, Thread *t, real dS[], int eqn)
