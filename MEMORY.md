# MEMORY.md - Long-term memory

## Role
- **Tom** - Decision layer for BinanceBot (paper trading) & Polymarket Scanner

## Operational Rules (CRITICAL)
**************** CRITICAL FILE RULE ****************
Before editing or creating any file:
1. locate the exact existing file path first
2. if the path is uncertain, search the project and confirm it
3. NEVER create a new file when a similarly named file already exists

If an edit fails:
1. read the file from disk
2. confirm the absolute path
3. retry the edit only after verification
**************** This rule must persist across resets.
1. **Python Edits:** NO partial string patches on live Python files.
   - Flow: Stop -> Edit Full Function/File -> Validate Syntax (`python3 -m py_compile`) -> Start.
2. **Shared File Edits:** Before editing shared files (e.g. `config.py`), RUN A DEPENDENCY CHECK (`grep -r`).
   - Do not remove legacy constants unless you verify 0 usages.
3. **Defensive Coding:**
   - Always check `if data:` before accessing indices/keys.
   - Use `traceback.print_exc()` in `try/except` blocks.
4. **Stability First:** Do not hot-patch the core loop repeatedly. Roll back on failure.

## Responsibilities
1. For each signal: APPROVE / REJECT / ADJUST
2. Base decisions on: trend alignment, risk-reward, market conditions, correlation risk
3. Default mode: PAPER trading
4. Conservative approach - quality over quantity

## Output Format per Signal
- Decision: APPROVE / REJECT / ADJUST
- Reason(s): bullet points
- If ADJUST: New levels (Entry, SL, TP1, TP2) + explanation
- If APPROVE: Brief reason why acceptable

## User Preferences
- **Channel:** Telegram (not webchat)
- **Updates:** Batch hourly (not every signal)
- **Logging:** Google Sheets (need to set up)
- **Model Preference:** Use Gemini 2.0 Flash for monitoring/background tasks where possible.

## Current Tasks
- Monitor BinanceBot (running - PID 175291)
- Monitor Polymarket Scanner (Phase 2: Maker-Ready running - PID 173991)
- Plan Phase 3: Market-Aware Paper Trading (Real orderbook, realistic fill sim, PnL ledger)

## BinanceBot State
- Location: /opt/binance-agent-bot/
- Status: Running (PID 175291)
- Logic: `run_agent.py` scans 5m TF, uses `ema_adx_stoch.py` + `indicators.py`.
- MTF filters: 15m regime + 5m timing + RR + ATR checks
- Max 2 open positions (enforced on NEW trades only; existing kept until closed).
- Deduplication: 15m cooldown per symbol/side.

## Polymarket Bot State
- Location: /root/.openclaw/workspace/polymarket_arb/
- Status: Running (PID 173991)
- Phase 2: Maker-Ready (JSON quotes generated, size capped at $10 due to missing OB).
