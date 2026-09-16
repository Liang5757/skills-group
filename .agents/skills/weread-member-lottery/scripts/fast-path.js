// Copy this function into cua_repl; reuse a connected App as `weread`.
async function wereadFastPath(app, {budgetMs = 20000, checkOnly = false} = {}) {
  const started = Date.now(), seen = new Set();
  const read = () => app.getAXState({disableDiffing: true, emit: false});
  let state = await read(), status = 'inspect_page';
  for (let turn = 0; turn < 7 && Date.now() - started < budgetMs; turn++) {
    if (/恭喜抽中/.test(state) && /奖励已存入/.test(state)) {status = 'existing_result'; break;}
    if (/验证码|扫码登录|登录后参与|活动已结束/.test(state)) {status = 'needs_attention'; break;}
    const rows = state.split('\n');
    const lottery = /ID: WRUI_Pressable_MembershipLottery-LotteryButton(?:,|$)/;
    const buttons = rows.filter(row => lottery.test(row));
    if (buttons.length > 1) break;
    if (buttons.length && (!/你已中奖/.test(buttons[0]) || checkOnly)) {
      status = /你已中奖|今日已抽|明日再来/.test(buttons[0]) ? 'already_drawn' : 'review_draw'; break;
    }
    const rules = buttons.length ? [lottery] : /会员抽奖/.test(state) && /付费会员可每日抽奖/.test(state)
      ? [/Description: 每日抽奖(?:,|$)/]
      : [/ID: id_cell_FreeCoin(?:,|$)/, /Description: 福利场(?:\s|,)/, /Value: 0, ID: id_home_tab_personal(?:,|$)/];
    const rule = rules.find(pattern => rows.some(row => pattern.test(row)));
    const matches = rule ? rows.filter(row => rule.test(row)) : [];
    const index = matches.length === 1 && matches[0].match(/^\s*(\d+)\s/);
    if (!index || seen.has(rule.source)) {
      const next = await app.getAXStateAndScreenshot({disableDiffing: true, emit: false});
      if (next.state === state) break;
      state = next.state; continue;
    }
    if (Date.now() - started >= budgetMs) break;
    await app.click(Number(index[1])); seen.add(rule.source);
    state = await read();
  }
  if (status === 'inspect_page') status = Date.now() - started >= budgetMs ? 'time_budget'
    : [...seen].some(key => key.includes('LotteryButton')) ? 'result_unconfirmed' : status;
  const screenshot = status === 'existing_result' ? await app.getScreenshot({emit: false}) : undefined;
  return {status, state, screenshot, elapsedMs: Date.now() - started};
}
if (typeof module !== 'undefined') module.exports = { wereadFastPath };
