"""Interactive MBS scenario dashboard generation."""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

from risk_engine.marketdata.models import YieldCurve
from risk_engine.services.mbs import MortgageScenarioResult


def _curve_payload(curve: YieldCurve) -> list[dict[str, float | str]]:
    payload: list[dict[str, float | str]] = []
    for point in curve.points:
        tenor = point.tenor.strip().upper()
        if tenor.endswith("D"):
            years = float(tenor[:-1]) / 365.25
        elif tenor.endswith("M"):
            years = float(tenor[:-1]) / 12.0
        elif tenor.endswith("Y"):
            years = float(tenor[:-1])
        else:
            continue
        payload.append({"years": years, "rate": point.rate, "label": point.tenor})
    return payload


def _default_inputs(result: MortgageScenarioResult) -> dict[str, float]:
    pool = result.pool
    return {
        "upb": pool.upb,
        "wac": pool.wac,
        "termMonths": float(pool.remaining_term_months),
        "seasoningMonths": float(pool.seasoning_months),
        "psa": result.psa,
        "marketRate": result.market_rate,
        "discountSpreadBps": result.discount_spread_bps,
        "refiSlopeCpr": result.refi_slope_cpr,
    }


def _escape_json(value: object) -> str:
    return html.escape(json.dumps(value, separators=(",", ":")))


def render_mbs_preview_svg(result: MortgageScenarioResult) -> str:
    """Render a compact static preview for the README."""

    periods = result.periods[:60] or result.periods
    width = 1200
    height = 640
    left = 80
    top = 72
    plot_w = width - left - 40
    plot_h = 360
    max_balance = max((period.beginning_balance for period in periods), default=1.0)
    max_cashflow = max((period.total_cashflow for period in periods), default=1.0)

    def x_pos(idx: int, count: int) -> float:
        if count <= 1:
            return left
        return left + (idx / (count - 1)) * plot_w

    def y_from(value: float, maximum: float) -> float:
        return top + plot_h - (value / maximum) * plot_h

    balance_points = [
        f"{x_pos(idx, len(periods)):.1f},{y_from(period.ending_balance, max_balance):.1f}"
        for idx, period in enumerate(periods)
    ]
    cash_points = [
        f"{x_pos(idx, len(periods)):.1f},{y_from(period.total_cashflow, max_cashflow):.1f}"
        for idx, period in enumerate(periods)
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="MBS scenario preview">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#f7fafc"/>
      <stop offset="100%" stop-color="#eef2f7"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="url(#bg)"/>
  <text x="{left}" y="42" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="700" fill="#132238">MBS Prepayment Lab Preview</text>
  <text x="{left}" y="66" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14" fill="#536271">Static preview for the README. The interactive dashboard recalculates these values live.</text>
  <g stroke="#d9e1ea" stroke-width="1">
    <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>
    <line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>
  </g>
  <polyline fill="none" stroke="#0f4c81" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{' '.join(balance_points)}"/>
  <polyline fill="none" stroke="#c47f00" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="{' '.join(cash_points)}" opacity="0.92"/>
  <g fill="#4b5a6a" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12">
    <text x="18" y="{top + 10}">${max_balance:,.0f}</text>
    <text x="18" y="{top + plot_h - 4}">$0</text>
    <text x="{left}" y="{top + plot_h + 22}">Month 1</text>
    <text x="{left + plot_w - 60}" y="{top + plot_h + 22}">Final Month</text>
    <rect x="{left}" y="{top + plot_h + 34}" width="14" height="14" fill="#0f4c81"/><text x="{left + 22}" y="{top + plot_h + 46}">Outstanding balance</text>
    <rect x="{left + 220}" y="{top + plot_h + 34}" width="14" height="14" fill="#c47f00"/><text x="{left + 242}" y="{top + plot_h + 46}">Monthly cash flow</text>
  </g>
  <g font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14" fill="#132238">
    <text x="{left}" y="596">PV: ${result.pv:,.0f}</text>
    <text x="{left + 230}" y="596">WAL: {result.wal_years:.2f} years</text>
    <text x="{left + 430}" y="596">Ending balance: ${result.ending_balance:,.0f}</text>
    <text x="{left + 710}" y="596">PSA: {result.psa:.0f}</text>
  </g>
</svg>"""


def render_mbs_dashboard_html(curve: YieldCurve, result: MortgageScenarioResult) -> str:
    """Render a self-contained interactive dashboard."""

    curve_payload = _curve_payload(curve)
    initial_inputs = _default_inputs(result)
    preview_uri = quote(render_mbs_preview_svg(result), safe="")

    template = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MBS Prepayment Lab</title>
  <style>
    :root {{
      --bg: #09111d;
      --panel: rgba(255,255,255,0.08);
      --border: rgba(255,255,255,0.12);
      --text: #edf3ff;
      --muted: #97a9c2;
      --blue: #4ea1ff;
      --gold: #f4b942;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(78,161,255,0.22), transparent 35%),
        radial-gradient(circle at top right, rgba(244,185,66,0.18), transparent 28%),
        linear-gradient(160deg, #07111f 0%, #101b2d 52%, #08101c 100%);
    }}
    .wrap {{ max-width: 1440px; margin: 0 auto; padding: 28px 22px 36px; }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
      align-items: end;
    }}
    h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 4rem); letter-spacing: -0.04em; }}
    .lede {{ color: var(--muted); line-height: 1.55; max-width: 74ch; margin: 10px 0 0; }}
    .pill-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .pill {{
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
      color: #dce7fb;
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.55fr 0.95fr;
      gap: 18px;
      align-items: start;
    }}
    .card {{
      border: 1px solid var(--border);
      border-radius: 24px;
      background: var(--panel);
      backdrop-filter: blur(16px);
      box-shadow: 0 18px 44px rgba(0,0,0,0.28);
    }}
    .body {{ padding: 18px; }}
    h2 {{ margin: 0 0 8px; font-size: 18px; letter-spacing: -0.02em; }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .section-title span, .small, .footer-note {{ color: var(--muted); }}
    .section-title span {{ font-size: 12px; }}
    .small {{ font-size: 12px; line-height: 1.45; }}
    .footer-note {{ margin-top: 16px; font-size: 13px; line-height: 1.55; }}
    .control {{
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      margin-bottom: 12px;
    }}
    .control label {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
      font-size: 13px;
      color: #dce7fb;
    }}
    .control input[type="range"] {{ width: 100%; }}
    .control input[type="number"] {{
      width: 98px;
      padding: 6px 8px;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.16);
      background: rgba(6, 12, 22, 0.95);
      color: var(--text);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .metric {{
      padding: 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
    }}
    .metric .label {{ font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
    .metric .value {{ font-size: 24px; font-weight: 700; letter-spacing: -0.03em; }}
    .metric .sub {{ font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.4; }}
    .chart {{
      padding: 14px 16px 10px;
    }}
    .chart svg {{ width: 100%; height: auto; display: block; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      overflow: hidden;
      border-radius: 16px;
    }}
    th, td {{
      padding: 10px 12px;
      font-size: 12px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      text-align: right;
    }}
    th {{
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      background: rgba(255,255,255,0.06);
      font-size: 11px;
    }}
    td:first-child, th:first-child {{ text-align: left; }}
    .svg-card {{ padding: 0; overflow: hidden; margin-top: 18px; }}
    @media (max-width: 1100px) {{
      .hero, .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>MBS Prepayment Lab</h1>
        <p class="lede">
          A desk-style scenario tool for mortgage-backed securities. Move the controls, reprice the pool, and see how
          PSA, refinance incentive, and discount spreads change projected cash flows against the Treasury curve.
        </p>
        <div class="pill-row">
          <div class="pill">PSA prepayment ramp</div>
          <div class="pill">Curve-based discounting</div>
          <div class="pill">PV and WAL</div>
          <div class="pill">Refi incentive stress</div>
        </div>
      </div>
      <div class="card body">
        <h2>Why it matters</h2>
        <div class="small">
          This is the kind of control surface an MBS desk actually uses when stress-testing how a pool behaves as rates
          move. It gives you the right knobs, the right outputs, and a curve anchor from live market data.
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card body">
        <div class="section-title">
          <h2>Scenario Controls</h2>
          <span>Live update</span>
        </div>
        <div class="control">
          <label><span>Current UPB</span><input id="upbVal" type="number" min="100000" step="50000"></label>
          <input id="upb" type="range" min="100000" max="200000000" step="50000">
        </div>
        <div class="control">
          <label><span>WAC (%)</span><input id="wacVal" type="number" min="0" step="0.125"></label>
          <input id="wac" type="range" min="1" max="12" step="0.125">
        </div>
        <div class="control">
          <label><span>Remaining Term (months)</span><input id="termMonthsVal" type="number" min="12" step="1"></label>
          <input id="termMonths" type="range" min="12" max="360" step="1">
        </div>
        <div class="control">
          <label><span>Seasoning (months)</span><input id="seasoningMonthsVal" type="number" min="0" step="1"></label>
          <input id="seasoningMonths" type="range" min="0" max="180" step="1">
        </div>
        <div class="control">
          <label><span>PSA (%)</span><input id="psaVal" type="number" min="0" step="5"></label>
          <input id="psa" type="range" min="0" max="300" step="5">
        </div>
        <div class="control">
          <label><span>Market Rate (%)</span><input id="marketRateVal" type="number" min="0" step="0.125"></label>
          <input id="marketRate" type="range" min="0.5" max="12" step="0.125">
        </div>
        <div class="control">
          <label><span>Discount Spread (bps)</span><input id="discountSpreadBpsVal" type="number" min="-200" step="5"></label>
          <input id="discountSpreadBps" type="range" min="-200" max="400" step="5">
        </div>
        <div class="control">
          <label><span>Refi Slope (CPR per 1% incentive)</span><input id="refiSlopeCprVal" type="number" min="0" step="0.5"></label>
          <input id="refiSlopeCpr" type="range" min="0" max="20" step="0.5">
        </div>

        <div class="card body" style="padding:0; margin-top:16px; background:rgba(255,255,255,0.03);">
          <div class="chart">
            <svg id="balanceChart" viewBox="0 0 900 360" preserveAspectRatio="none"></svg>
          </div>
          <div class="chart">
            <svg id="cashflowChart" viewBox="0 0 900 260" preserveAspectRatio="none"></svg>
          </div>
        </div>
      </div>

      <div class="card body">
        <div class="section-title">
          <h2>Scenario Metrics</h2>
          <span>Treasury anchored</span>
        </div>
        <div class="metrics">
          <div class="metric"><div class="label">Present Value</div><div class="value" id="pvText"></div><div class="sub" id="pvSub"></div></div>
          <div class="metric"><div class="label">WAL</div><div class="value" id="walText"></div><div class="sub" id="walSub"></div></div>
          <div class="metric"><div class="label">Ending Balance</div><div class="value" id="endingBalanceText"></div><div class="sub" id="endingBalanceSub"></div></div>
          <div class="metric"><div class="label">Eff. CPR</div><div class="value" id="cprText"></div><div class="sub" id="cprSub"></div></div>
        </div>
        <div class="footer-note" id="summaryText"></div>
        <div class="footer-note" id="curveText"></div>

        <div style="margin-top:18px;">
          <div class="section-title">
            <h2>Monthly Schedule</h2>
            <span>First 12 periods</span>
          </div>
          <div class="small">Scheduled principal, prepay, and remaining balance update with every control change.</div>
          <table>
            <thead>
              <tr>
                <th>Month</th>
                <th>Beg. Bal.</th>
                <th>Interest</th>
                <th>Sched. Prin.</th>
                <th>Prepay</th>
                <th>End Bal.</th>
              </tr>
            </thead>
            <tbody id="scheduleBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card svg-card">
      <img alt="MBS preview snapshot" src="data:image/svg+xml;charset=utf-8,{preview_uri}" style="display:block;width:100%;height:auto;">
    </div>
  </div>

  <script>
    const curvePoints = {_escape_json(curve_payload)};
    const defaults = {_escape_json(initial_inputs)};

    const controls = {{
      upb: document.getElementById('upb'),
      upbVal: document.getElementById('upbVal'),
      wac: document.getElementById('wac'),
      wacVal: document.getElementById('wacVal'),
      termMonths: document.getElementById('termMonths'),
      termMonthsVal: document.getElementById('termMonthsVal'),
      seasoningMonths: document.getElementById('seasoningMonths'),
      seasoningMonthsVal: document.getElementById('seasoningMonthsVal'),
      psa: document.getElementById('psa'),
      psaVal: document.getElementById('psaVal'),
      marketRate: document.getElementById('marketRate'),
      marketRateVal: document.getElementById('marketRateVal'),
      discountSpreadBps: document.getElementById('discountSpreadBps'),
      discountSpreadBpsVal: document.getElementById('discountSpreadBpsVal'),
      refiSlopeCpr: document.getElementById('refiSlopeCpr'),
      refiSlopeCprVal: document.getElementById('refiSlopeCprVal'),
      pvText: document.getElementById('pvText'),
      pvSub: document.getElementById('pvSub'),
      walText: document.getElementById('walText'),
      walSub: document.getElementById('walSub'),
      endingBalanceText: document.getElementById('endingBalanceText'),
      endingBalanceSub: document.getElementById('endingBalanceSub'),
      cprText: document.getElementById('cprText'),
      cprSub: document.getElementById('cprSub'),
      summaryText: document.getElementById('summaryText'),
      curveText: document.getElementById('curveText'),
      scheduleBody: document.getElementById('scheduleBody'),
      balanceChart: document.getElementById('balanceChart'),
      cashflowChart: document.getElementById('cashflowChart'),
    }};

    function fmtMoney(value) {{
      return new Intl.NumberFormat('en-US', {{ style: 'currency', currency: 'USD', maximumFractionDigits: 0 }}).format(value);
    }}

    function fmtPct(value, digits = 2) {{
      return `${{value.toFixed(digits)}}%`;
    }}

    function fmtNum(value, digits = 2) {{
      return Number(value).toFixed(digits);
    }}

    function monthlyRate(annualPct) {{
      return annualPct / 1200.0;
    }}

    function monthlyPayment(balance, annualPct, months) {{
      if (months <= 0) return 0;
      const r = monthlyRate(annualPct);
      if (r === 0) return balance / months;
      const factor = Math.pow(1 + r, months);
      return balance * (r * factor) / (factor - 1);
    }}

    function standardCpr(ageMonths) {{
      return Math.min(0.2 * Math.min(Math.max(ageMonths, 0), 30), 6.0);
    }}

    function smmFromCpr(cpr) {{
      const bounded = Math.min(Math.max(cpr, 0), 99);
      return 1 - Math.pow(1 - bounded / 100, 1 / 12);
    }}

    function curveRate(years) {{
      if (!curvePoints.length) return 0;
      if (years <= curvePoints[0].years) return curvePoints[0].rate;
      for (let i = 0; i < curvePoints.length - 1; i++) {{
        const left = curvePoints[i];
        const right = curvePoints[i + 1];
        if (years >= left.years && years <= right.years) {{
          const t = (years - left.years) / (right.years - left.years);
          return left.rate + t * (right.rate - left.rate);
        }}
      }}
      return curvePoints[curvePoints.length - 1].rate;
    }}

    function readFloat(id) {{
      return parseFloat(controls[id].value);
    }}

    function simulateScenario() {{
      const upb = readFloat('upb');
      const wac = readFloat('wac');
      const termMonths = Math.max(1, Math.round(readFloat('termMonths')));
      const seasoningMonths = Math.max(0, Math.round(readFloat('seasoningMonths')));
      const psa = readFloat('psa');
      const marketRate = readFloat('marketRate');
      const discountSpreadBps = readFloat('discountSpreadBps');
      const refiSlopeCpr = readFloat('refiSlopeCpr');

      const payment = monthlyPayment(upb, wac, termMonths);
      let balance = upb;
      let pv = 0;
      let totalInterest = 0;
      let totalPrincipal = 0;
      let weightedMonths = 0;
      const periods = [];

      for (let month = 1; month <= termMonths; month++) {{
        if (balance <= 1e-8) break;
        const ageMonths = seasoningMonths + month;
        const interest = balance * monthlyRate(wac);
        const scheduledPrincipal = Math.min(Math.max(payment - interest, 0), balance);
        const afterSched = Math.max(balance - scheduledPrincipal, 0);
        const psaCpr = standardCpr(ageMonths) * (psa / 100.0);
        const incentive = Math.max(wac - marketRate, 0);
        const incentiveCpr = Math.min(incentive * refiSlopeCpr, 30);
        const effectiveCpr = Math.min(psaCpr + incentiveCpr, 60);
        const smm = smmFromCpr(effectiveCpr);
        const prepaymentPrincipal = Math.min(afterSched * smm, afterSched);
        const totalPrincipalMonth = scheduledPrincipal + prepaymentPrincipal;
        const totalCashflow = interest + totalPrincipalMonth;
        const endingBalance = Math.max(balance - totalPrincipalMonth, 0);
        const discountYears = ageMonths / 12.0;
        const discountRate = curveRate(discountYears) + discountSpreadBps / 100.0;
        const presentValue = totalCashflow / Math.pow(1 + discountRate / 100.0, discountYears);

        pv += presentValue;
        totalInterest += interest;
        totalPrincipal += totalPrincipalMonth;
        weightedMonths += month * totalPrincipalMonth;

        periods.push({{
          month,
          ageMonths,
          beginningBalance: balance,
          interest,
          scheduledPrincipal,
          prepaymentPrincipal,
          totalPrincipal: totalPrincipalMonth,
          totalCashflow,
          endingBalance,
          discountRate,
          presentValue,
          effectiveCpr,
        }});

        balance = endingBalance;
      }}

      return {{
        upb,
        wac,
        termMonths,
        seasoningMonths,
        psa,
        marketRate,
        discountSpreadBps,
        refiSlopeCpr,
        payment,
        pv,
        totalInterest,
        totalPrincipal,
        endingBalance: balance,
        walYears: totalPrincipal > 0 ? (weightedMonths / totalPrincipal) / 12.0 : 0,
        periods,
      }};
    }}

    function minMax(values) {{
      const filtered = values.filter(v => Number.isFinite(v));
      return [Math.min(...filtered), Math.max(...filtered)];
    }}

    function lineChart(data, width, height, stroke, title, yFormatter) {{
      const padding = {{ left: 72, right: 20, top: 24, bottom: 36 }};
      const plotW = width - padding.left - padding.right;
      const plotH = height - padding.top - padding.bottom;
      const ys = data.map(d => d.value);
      const [minY, maxY] = minMax(ys);
      const yPad = Math.max((maxY - minY) * 0.12, maxY * 0.05, 0.1);
      const y0 = minY - yPad;
      const y1 = maxY + yPad;
      const xScale = i => padding.left + (data.length <= 1 ? 0 : (i / (data.length - 1)) * plotW);
      const yScale = y => padding.top + plotH - ((y - y0) / Math.max(y1 - y0, 1e-9)) * plotH;
      const points = data.map((d, i) => `${{xScale(i).toFixed(1)}},${{yScale(d.value).toFixed(1)}}`).join(' ');
      const xTicks = [];
      const tickCount = Math.min(5, data.length);
      for (let i = 0; i < tickCount; i++) {{
        const idx = Math.round((data.length - 1) * (i / Math.max(tickCount - 1, 1)));
        const x = xScale(idx);
        xTicks.push(`<line x1="${{x.toFixed(1)}}" y1="${{padding.top + plotH}}" x2="${{x.toFixed(1)}}" y2="${{padding.top + plotH + 5}}" stroke="#7b8ca4" />`);
        xTicks.push(`<text x="${{x.toFixed(1)}}" y="${{padding.top + plotH + 18}}" text-anchor="middle">${{idx + 1}}</text>`);
      }}
      const yTicks = [];
      for (let i = 0; i < 4; i++) {{
        const value = y0 + (y1 - y0) * (i / 3);
        const y = yScale(value);
        yTicks.push(`<line x1="${{padding.left}}" y1="${{y.toFixed(1)}}" x2="${{padding.left + plotW}}" y2="${{y.toFixed(1)}}" stroke="#d6ddea" stroke-dasharray="4 4" opacity="0.55" />`);
        yTicks.push(`<text x="${{padding.left - 12}}" y="${{(y + 4).toFixed(1)}}" text-anchor="end">${{yFormatter(value)}}</text>`);
      }}
      return `
        <svg viewBox="0 0 ${{width}} ${{height}}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="${{width}}" height="${{height}}" rx="18" fill="rgba(255,255,255,0.04)" />
          <text x="20" y="22" fill="#edf3ff" font-size="14" font-weight="700">${{title}}</text>
          ${{yTicks.join('')}}
          <line x1="${{padding.left}}" y1="${{padding.top + plotH}}" x2="${{padding.left + plotW}}" y2="${{padding.top + plotH}}" stroke="#7b8ca4" />
          <line x1="${{padding.left}}" y1="${{padding.top}}" x2="${{padding.left}}" y2="${{padding.top + plotH}}" stroke="#7b8ca4" />
          <polyline fill="none" stroke="${{stroke}}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${{points}}" />
          ${{xTicks.join('')}}
        </svg>
      `;
    }}

    function renderScenario() {{
      const scenario = simulateScenario();
      const first = scenario.periods.slice(0, 12);
      const effectiveCpr = scenario.periods.length ? scenario.periods[0].effectiveCpr : 0;
      const finalAgeYears = scenario.periods.length ? scenario.periods[scenario.periods.length - 1].ageMonths / 12.0 : 0;
      const curveSpot = scenario.periods.length ? curveRate(finalAgeYears) : 0;

      controls.pvText.textContent = fmtMoney(scenario.pv);
      controls.pvSub.textContent = `${{fmtPct((scenario.pv / scenario.upb) * 100, 1)}} of current UPB`;
      controls.walText.textContent = fmtNum(scenario.walYears, 2) + ' yrs';
      controls.walSub.textContent = `Monthly payment ${{fmtMoney(scenario.payment)}}`;
      controls.endingBalanceText.textContent = fmtMoney(scenario.endingBalance);
      controls.endingBalanceSub.textContent = `Remaining after ${{scenario.periods.length}} months`;
      controls.cprText.textContent = fmtPct(effectiveCpr, 2);
      controls.cprSub.textContent = `PSA ${{fmtNum(scenario.psa, 0)}} / market ${{fmtNum(scenario.marketRate, 2)}}%`;
      controls.summaryText.textContent = `Discount spread: ${{fmtNum(scenario.discountSpreadBps, 0)}} bps | refi slope: ${{fmtNum(scenario.refiSlopeCpr, 1)}} CPR per 1% incentive.`;
      controls.curveText.textContent = `Curve anchor: 10Y Treasury ${{fmtNum(curveRate(10), 3)}}% | spot at final maturity ${{fmtNum(curveSpot, 3)}}%.`;

      controls.balanceChart.innerHTML = lineChart(
        scenario.periods.map(p => ({{ value: p.endingBalance }})),
        900,
        360,
        '#4ea1ff',
        'Outstanding Balance',
        v => fmtMoney(v / 1000) + 'k'
      );
      controls.cashflowChart.innerHTML = lineChart(
        scenario.periods.map(p => ({{ value: p.totalCashflow }})),
        900,
        260,
        '#f4b942',
        'Monthly Cash Flow',
        v => fmtMoney(v)
      );

      controls.scheduleBody.innerHTML = first.map(p => `
        <tr>
          <td>${{p.month}}</td>
          <td>${{fmtMoney(p.beginningBalance)}}</td>
          <td>${{fmtMoney(p.interest)}}</td>
          <td>${{fmtMoney(p.scheduledPrincipal)}}</td>
          <td>${{fmtMoney(p.prepaymentPrincipal)}}</td>
          <td>${{fmtMoney(p.endingBalance)}}</td>
        </tr>
      `).join('');
    }}

    Object.keys(defaults).forEach(id => {{
      controls[id].value = defaults[id];
      controls[id + 'Val'].value = defaults[id];
    }});

    ['upb', 'wac', 'termMonths', 'seasoningMonths', 'psa', 'marketRate', 'discountSpreadBps', 'refiSlopeCpr'].forEach(id => {{
      controls[id].addEventListener('input', () => {{
        controls[id + 'Val'].value = controls[id].value;
        renderScenario();
      }});
      controls[id + 'Val'].addEventListener('input', () => {{
        controls[id].value = controls[id + 'Val'].value;
        renderScenario();
      }});
    }});

    renderScenario();
  </script>
</body>
</html>"""

    return template


def write_mbs_dashboard_assets(
    curve: YieldCurve,
    result: MortgageScenarioResult,
    *,
    html_path: str | Path,
    preview_svg_path: str | Path,
) -> tuple[Path, Path]:
    """Write the interactive HTML dashboard and static preview assets."""

    html_target = Path(html_path)
    svg_target = Path(preview_svg_path)
    html_target.write_text(render_mbs_dashboard_html(curve, result), encoding="utf-8")
    svg_target.write_text(render_mbs_preview_svg(result), encoding="utf-8")
    return html_target, svg_target
