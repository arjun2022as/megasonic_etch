/* Minimal stand-in for Fluent's udf.h, ONLY for a local syntax/type check of etch.c (clang -fsyntax-only).
   Macro shapes follow the Fluent UDF manual; nothing here is used on the cluster. */
/* no system headers on the laptop: declare what the UDF uses */
#define NULL ((void *)0)
double sqrt(double); double fabs(double); double pow(double, double); double cos(double); double sin(double);
double exp(double);
typedef struct file_struct FILE;
FILE *fopen(const char *, const char *); int fclose(FILE *); int fprintf(FILE *, const char *, ...);
int sprintf(char *, const char *, ...);
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
/* added for the current etch.c and resolved_extra.c */
#define begin_c_loop_all(c, t) for (c = 0; c < 10; c++)
#define end_c_loop_all(c, t)
#define thread_loop_f(t, d) for (t = next_c_thread(d, NULL); t != NULL; t = next_c_thread(d, t))
#define c_face_loop(c, t, n) for (n = 0; n < 4; n++)
face_t cface(cell_t c, Thread *t, int n);
Thread *cfthread(cell_t c, Thread *t, int n);
#define C_FACE(c, t, n) cface(c, t, n)
#define C_FACE_THREAD(c, t, n) cfthread(c, t, n)
void *tstore(Thread *t, int sv);
#define THREAD_STORAGE(t, sv) tstore(t, sv)
#define SV_UDM_I 1
#define SV_UDS_I(i) (10 + (i))
#define SV_FLUX 2
#define NNULLP(p) ((p) != NULL)
#define THREAD_ID(t) ((t)->id)
void Message(const char *fmt, ...);
real flow_time(void);
#define CURRENT_TIME flow_time()
typedef struct node_struct { real x[2]; } Node;
Node *cnode(cell_t c, Thread *t, int k);
#define c_node_loop(c, t, k) for (k = 0; k < 4; k++)
#define C_NODE(c, t, k) cnode(c, t, k)
#define NODE_X(nd) ((nd)->x[0])
