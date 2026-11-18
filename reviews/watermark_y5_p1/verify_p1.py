"""Deterministic P1 checks; no random seeds or Monte Carlo."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'simulation'))
from model import load_model
from engine import simulate

model = load_model(ROOT / 'simulation/config.json')
c = model.cfg
N, n, T = c['N'], c['n'], c['T']
mix = np.eye(N)
for j, i in model.edges:
    mix[i, i] -= c['epsilon']
    mix[i, j] += c['epsilon']
B = np.kron(mix, model.A)
F = np.stack([B - np.block([[model.gains[t,i] @ model.H[i] if i == j else np.zeros((n,n)) for j in range(N)] for i in range(N)]) for t in range(T)])
G = np.zeros((N*n,n)); G[n:2*n] = c['epsilon'] * model.A
Qjoint = np.kron(np.ones((N,N)), model.Q)
P = np.kron(np.ones((N,N)), model.P0)
cov_error = 0.0
for t in range(T):
    noise = Qjoint.copy()
    for i in range(N):
        s = slice(i*n,(i+1)*n); K = model.gains[t,i]
        noise[s,s] += K @ model.R[i] @ K.T
    P = F[t] @ P @ F[t].T + noise
    cov_error = max(cov_error, np.max(np.abs(P-model.nominal_covariance[t+1])))

# Deterministic signals, direct node updates compared with the stacked recurrence.
healthy = np.zeros((N,n)); attacked = healthy.copy(); d = np.zeros(N*n)
max_error = 0.0; mse_error = 0.0; decode_error = 0.0
for t in range(T):
    y = np.array([[np.sin(.01*t+i),np.cos(.013*t-i)] for i in range(N)])
    beta = np.array([.2*np.sin(t*.03), .3*np.cos(t*.02)])
    M = 1.1*np.eye(n)+np.outer(beta,beta)
    a = np.array([.3,-.2]) if 200 <= t <= 249 else np.zeros(n)
    packet = np.linalg.solve(M, attacked[0]); received = M @ (packet+a)
    decode_error = max(decode_error, np.max(np.abs(received-attacked[0]-M@a)))
    def update(hat, injection):
        out = np.empty_like(hat)
        for i in range(N):
            out[i] = model.A@hat[i]+model.gains[t,i]@(y[i]-model.H[i]@hat[i])
            for j, receiver in model.edges:
                if receiver == i:
                    msg = hat[j] + (injection if (j,i)==(0,1) else 0)
                    out[i] += c['epsilon']*model.A@(msg-hat[i])
        return out
    healthy = update(healthy, np.zeros(n)); attacked = update(attacked, received-attacked[0])
    d = F[t]@d + G@M@a
    max_error = max(max_error, np.max(np.abs((attacked-healthy).reshape(-1)-d)))
    x = np.array([np.sin(t*.007),np.cos(t*.009)])
    e = (healthy-x).reshape(-1)
    mse_error = max(mse_error,abs(np.sum((attacked-x)**2)-np.sum((healthy-x)**2)-d@d-2*e@d))

# Existing engine: deterministic clean and constant decoded attack, all sends.
x = np.zeros((1,T+1,n)); y = np.zeros((1,T,N,n)); schedule = np.ones((1,T,N),dtype=bool)
clean = simulate(model,x,y,[0],schedule=schedule,collect=False)
bad = simulate(model,x,y,[0],scenario='step',schedule=schedule,collect=False)
d = np.zeros(N*n); engine_error = 0.0
for t in range(T):
    v = np.asarray(c['attack']['bias']) if 200 <= t <= 249 else np.zeros(n)
    d = F[t]@d+G@v
    engine_error = max(engine_error,np.max(np.abs((bad.estimates[0,t+1]-clean.estimates[0,t+1]).reshape(-1)-d)))
results = {'covariance_max_abs':cov_error,'recurrence_max_abs':max_error,'decode_max_abs':decode_error,'mse_identity_max_abs':mse_error,'engine_max_abs':engine_error,'mean_trace_P400':sum(np.trace(P[i*n:(i+1)*n,i*n:(i+1)*n]) for i in range(N))/N,'minimum_P400_eigenvalue':np.linalg.eigvalsh(P)[0]}
for key,value in results.items(): print(f'{key}: {value:.12g}')
assert max(cov_error,max_error,decode_error,mse_error,engine_error) < 1e-9
