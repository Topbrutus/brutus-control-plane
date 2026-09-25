from __future__ import annotations

import itertools
import json
import math
import time
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np
import sympy

def primes_for(Q: int) -> list[int]:
    return list(sympy.primerange(5, Q + 1))

def make_spf(limit: int) -> np.ndarray:
    spf = np.zeros(limit + 1, dtype=np.int32)
    for p in sympy.primerange(2, int(limit ** 0.5) + 1):
        view = spf[p * p :: p]
        mask = view == 0
        view[mask] = p
    return spf

def factor_spf(n: int, spf: np.ndarray) -> list[int]:
    out = []
    while n > 1:
        p = int(spf[n])
        if p == 0:
            out.append(n)
            break
        out.append(p)
        while n % p == 0:
            n //= p
    return out

def log_series_primary(T: list[Decimal], kmax: int) -> list[Decimal]:
    x = [Decimal(0)] * (kmax + 1)
    for k in range(2, kmax + 1):
        x[k] = T[k]
    out = [Decimal(0)] * (kmax + 1)
    power = x[:]
    for m in range(1, kmax + 1):
        coef = (Decimal(1) if m % 2 else Decimal(-1)) / Decimal(m)
        for k in range(kmax + 1):
            out[k] += coef * power[k]
        nxt = [Decimal(0)] * (kmax + 1)
        for i in range(2, kmax + 1):
            if not power[i]:
                continue
            for j in range(2, kmax + 1 - i):
                if x[j]:
                    nxt[i + j] += power[i] * x[j]
        power = nxt
    return out

def poly_mul_linear(poly: list[Decimal], z: Decimal) -> list[Decimal]:
    out = [Decimal(0)] * len(poly)
    out[0] = poly[0]
    for k in range(1, len(poly)):
        out[k] = poly[k] + z * poly[k - 1]
    return out

def poly_replace(poly: list[Decimal], z0: Decimal, z1: Decimal) -> list[Decimal]:
    q = [Decimal(0)] * len(poly)
    q[0] = poly[0]
    for k in range(1, len(poly)):
        q[k] = poly[k] - z0 * q[k - 1]
    return poly_mul_linear(q, z1)

def primary_compute(cfg: dict) -> dict:
    X, Q, kmax = cfg['X'], cfg['Q'], cfg['kmax']
    getcontext().prec = cfg['precision']
    D = Decimal
    primes = primes_for(Q)
    spf = make_spf(X)
    cnt, pair, pat = Counter(), Counter(), Counter()
    n = 0
    for t in range(1, X + 1, 2):
        if sympy.isprime(72 * t * t + 1):
            n += 1
            qs = tuple(sorted(q for q in factor_spf(t, spf) if 5 <= q <= Q))
            pat[qs] += 1
            for q in qs:
                cnt[q] += 1
            for a, b in itertools.combinations(qs, 2):
                pair[a, b] += 1
    N = D(n)
    f = {q: D(cnt[q]) / N for q in primes}
    z0 = {q: D(cnt[q]) / (N * D(q) - D(cnt[q])) for q in primes}
    z1 = {q: -(N - D(cnt[q])) / (N * D(q) - D(cnt[q])) for q in primes}
    base = [D(0)] * (kmax + 1)
    base[0] = D(1)
    for q in primes:
        base = poly_mul_linear(base, z0[q])
    sums = [D(0)] * (kmax + 1)
    meanw = D(0)
    for qs, c in pat.items():
        poly = base[:]
        w = D(1)
        for q in qs:
            poly = poly_replace(poly, z0[q], z1[q])
            w *= D(q - 1) / D(q)
        cc = D(c)
        meanw += cc * w
        for k in range(2, kmax + 1):
            sums[k] += cc * poly[k]
    T = [x / N for x in sums]
    meanw /= N
    C = D(1)
    for q in primes:
        C *= D(1) - f[q] / D(q)
    Ec = meanw / C
    P = [D(0)] * (kmax // 2 + 1)
    pairlog = D(0)
    for ia, q in enumerate(primes):
        muq = D(1) - f[q] / D(q)
        for r in primes[ia + 1:]:
            mur = D(1) - f[r] / D(r)
            fqr = D(pair[q, r]) / N
            p = (fqr - f[q] * f[r]) / (D(q * r) * muq * mur)
            pairlog += (D(1) + p).ln()
            v = D(1)
            for m in range(1, len(P)):
                v *= p
                P[m] += v
    K = log_series_primary(T, kmax)
    for m in range(1, len(P)):
        K[2 * m] -= (D(1) if m % 2 else D(-1)) * P[m] / D(m)
    L = Ec.ln() - pairlog
    return {
        'status':'PASS','algorithm_id':'pattern-decimal-polynomial-v1',
        'candidate_count':n,'pattern_count':len(pat),
        'D':str(L),'T':{str(k):str(T[k]) for k in range(2,kmax+1)},
        'K':{str(k):str(K[k]) for k in range(3,kmax+1)},
        'partial':str(sum(K[3:],D(0))),
        'relative_residual':str((L-sum(K[3:],D(0)))/L)
    }

def collect_rows_factorint(cfg: dict):
    X, Q = cfg['X'], cfg['Q']
    rows = []
    cnt, pair = Counter(), Counter()
    meanw_num = Decimal(0)
    for t in range(1, X + 1, 2):
        if not sympy.isprime(72 * t * t + 1):
            continue
        fs = sympy.factorint(t)
        qs = tuple(sorted(q for q in fs if 5 <= q <= Q))
        rows.append(qs)
        for q in qs:
            cnt[q] += 1
        for a,b in itertools.combinations(qs,2):
            pair[a,b] += 1
    return rows,cnt,pair

def mirror_compute(cfg: dict) -> dict:
    getcontext().prec = cfg['precision']
    D = Decimal
    Q,kmax = cfg['Q'],cfg['kmax']
    primes = primes_for(Q)
    rows,cnt,pair = collect_rows_factorint(cfg)
    n=len(rows); N=D(n)
    f={q:D(cnt[q])/N for q in primes}
    z0={q:D(cnt[q])/(N*D(q)-D(cnt[q])) for q in primes}
    z1={q:-(N-D(cnt[q]))/(N*D(q)-D(cnt[q])) for q in primes}
    base_p=[D(0)]*(kmax+1); delta={}
    for q in primes:
        for k in range(1,kmax+1):
            base_p[k]+=z0[q]**k
        delta[q]=[D(0)]+[z1[q]**k-z0[q]**k for k in range(1,kmax+1)]
    sums=[D(0)]*(kmax+1); meanw=D(0)
    for qs in rows:
        ps=base_p[:]
        w=D(1)
        for q in qs:
            w*=D(q-1)/D(q)
            dq=delta[q]
            for k in range(1,kmax+1):
                ps[k]+=dq[k]
        meanw+=w
        e=[D(0)]*(kmax+1); e[0]=D(1)
        for k in range(1,kmax+1):
            acc=D(0)
            for i in range(1,k+1):
                acc += (D(1) if i%2 else D(-1))*e[k-i]*ps[i]
            e[k]=acc/D(k)
        for k in range(2,kmax+1):
            sums[k]+=e[k]
    T=[x/N for x in sums]; meanw/=N
    C=D(1)
    for q in primes:
        C*=D(1)-f[q]/D(q)
    Ec=meanw/C
    P=[D(0)]*(kmax//2+1); pairlog=D(0)
    for ia,q in enumerate(primes):
        muq=D(1)-f[q]/D(q)
        for r in primes[ia+1:]:
            mur=D(1)-f[r]/D(r)
            fqr=D(pair[q,r])/N
            p=(fqr-f[q]*f[r])/(D(q*r)*muq*mur)
            pairlog+=(D(1)+p).ln()
            v=D(1)
            for m in range(1,len(P)):
                v*=p; P[m]+=v
    # Independent log-coefficient recurrence: n*T_n=sum_{j=1}^n j*L_j*T_{n-j}.
    S=[D(0)]*(kmax+1); S[0]=D(1)
    for k in range(2,kmax+1): S[k]=T[k]
    Lc=[D(0)]*(kmax+1)
    for ndeg in range(1,kmax+1):
        subtotal=sum((D(j)*Lc[j]*S[ndeg-j] for j in range(1,ndeg)),D(0))
        Lc[ndeg]=S[ndeg]-subtotal/D(ndeg)
    K=Lc[:]
    for m in range(1,len(P)):
        K[2*m]-=(D(1) if m%2 else D(-1))*P[m]/D(m)
    dust=Ec.ln()-pairlog
    partial=sum(K[3:],D(0))
    return {
        'status':'PASS','algorithm_id':'row-newton-logrecurrence-v1',
        'candidate_count':n,'D':str(dust),
        'K':{str(k):str(K[k]) for k in range(3,kmax+1)},
        'partial':str(partial),'relative_residual':str((dust-partial)/dust)
    }

def countertest(cfg: dict) -> dict:
    Q=cfg['Q']; primes=primes_for(Q)
    rows,cnt,pair=collect_rows_factorint(cfg)
    n=len(rows); pat=Counter(rows)
    den=1; base=1; A={}; B={}
    for q in primes:
        c=cnt[q]; dq=n*q-c; aq=n*q+3*c; bq=n*(q+4)-5*c
        den*=dq; base*=aq; A[q]=aq; B[q]=bq
    numsum=0
    for qs,count in pat.items():
        num=base
        for q in qs:
            num=(num//A[q])*B[q]
        numsum+=count*num
    exact_b4_lt_1 = numsum < 2*n*den
    pair_r4=True; worst_num=0; worst_den=1; worst=None
    for ia,q in enumerate(primes):
        cq=cnt[q]
        for r in primes[ia+1:]:
            cr=cnt[r]; cqr=pair[q,r]
            pn=abs(cqr*n-cq*cr); pd=(n*q-cq)*(n*r-cr)
            if 16*pn>=pd: pair_r4=False
            if pn*worst_den>worst_num*pd:
                worst_num,worst_den,worst=pn,pd,(q,r)
    return {
        'status':'PASS' if exact_b4_lt_1 and pair_r4 else 'FAIL',
        'algorithm_id':'integer-rational-rouche-countertest-v1',
        'candidate_count':n,'exact_b4_lt_1':exact_b4_lt_1,
        'b4_margin_fraction':str(Decimal(2*n*den-numsum)/Decimal(2*n*den)),
        'pair_zero_free_r4':pair_r4,'worst_pair':worst,
        'max_abs_p':str(Decimal(worst_num)/Decimal(worst_den))
    }

def precision_audit(cfg: dict) -> dict:
    getcontext().prec=cfg['precision']
    D=Decimal; Q=cfg['Q']; primes=primes_for(Q)
    rows,cnt,pair=collect_rows_factorint(cfg); n=len(rows); N=D(n)
    mean_dec=D(0); mean_float=0.0
    for qs in rows:
        wd=D(1); wf=1.0
        for q in qs:
            wd*=D(q-1)/D(q); wf*=1.0-1.0/q
        mean_dec+=wd; mean_float+=wf
    mean_dec/=N; mean_float/=n
    Cdec=D(1); Cfloat=1.0; pairlog_dec=D(0); pairlog_float=0.0
    fdec={q:D(cnt[q])/N for q in primes}
    for q in primes:
        Cdec*=D(1)-fdec[q]/D(q); Cfloat*=1.0-(cnt[q]/n)/q
    for ia,q in enumerate(primes):
        fq=fdec[q]; muq=D(1)-fq/D(q)
        for r in primes[ia+1:]:
            fr=fdec[r]; mur=D(1)-fr/D(r); fqr=D(pair[q,r])/N
            pd=(fqr-fq*fr)/(D(q*r)*muq*mur)
            pf=(pair[q,r]/n-(cnt[q]/n)*(cnt[r]/n))/(q*r*(1-(cnt[q]/n)/q)*(1-(cnt[r]/n)/r))
            pairlog_dec+=(D(1)+pd).ln(); pairlog_float+=math.log1p(pf)
    dust_dec=(mean_dec/Cdec).ln()-pairlog_dec
    dust_float=math.log(mean_float/Cfloat)-pairlog_float
    rel=abs((D(str(dust_float))-dust_dec)/dust_dec)
    return {
        'status':'PASS','algorithm_id':'decimal-vs-float64-audit-v1',
        'candidate_count':n,'D_decimal':str(dust_dec),'D_float64':repr(dust_float),
        'relative_delta':str(rel),'precision_wall_detected':rel>D('1e-10')
    }

def arbiter(cfg: dict, job_dir: Path) -> dict:
    timeout=time.time()+cfg.get('arbiter_timeout_seconds',600)
    paths=[job_dir/f'POSTE-{i:02d}.json' for i in range(1,5)]
    while time.time()<timeout and not all(p.exists() for p in paths):
        time.sleep(0.2)
    if not all(p.exists() for p in paths):
        return {'status':'FAIL','algorithm_id':'trace-arbiter-v1','reason':'worker_timeout'}
    rs=[json.loads(p.read_text(encoding='utf-8')) for p in paths]
    if any(r.get('status')!='PASS' for r in rs):
        return {'status':'FAIL','algorithm_id':'trace-arbiter-v1','reason':'upstream_failure'}
    primary,mirror,counter,precision=[r['payload'] for r in rs]
    getcontext().prec=cfg['precision']
    D=Decimal
    dd=abs((D(primary['D'])-D(mirror['D']))/D(primary['D']))
    kdiff={}
    for k in primary['K']:
        a=D(primary['K'][k]); b=D(mirror['K'][k])
        scale=max(abs(a),D('1e-60'))
        kdiff[k]=abs(a-b)/scale
    tol=D(cfg.get('arbiter_relative_tolerance','1e-45'))
    checks={
        'candidate_count_match':primary['candidate_count']==mirror['candidate_count']==counter['candidate_count']==precision['candidate_count'],
        'D_independent_match':dd<=tol,
        'K_independent_match':all(v<=tol for v in kdiff.values()),
        'exact_b4_lt_1':counter['exact_b4_lt_1'],
        'pair_zero_free_r4':counter['pair_zero_free_r4'],
        'precision_audit_completed':True
    }
    status='PASS' if all(checks.values()) else 'FAIL'
    return {
        'status':status,'algorithm_id':'trace-arbiter-v1','checks':checks,
        'D_relative_difference':str(dd),
        'K_relative_differences':{k:str(v) for k,v in kdiff.items()},
        'precision_wall_detected':precision['precision_wall_detected']
    }

def run_role(role: str, config: dict, job_dir: Path) -> dict:
    cfg=config['experiment']
    if role=='PRIMARY': return primary_compute(cfg)
    if role=='MIRROR': return mirror_compute(cfg)
    if role=='COUNTERTEST': return countertest(cfg)
    if role=='PRECISION': return precision_audit(cfg)
    if role=='ARBITER': return arbiter(cfg,job_dir)
    raise ValueError(role)
