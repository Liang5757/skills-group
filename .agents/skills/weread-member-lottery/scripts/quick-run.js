// Normal observed UI route; unexpected pages are returned for inspection.
async function wereadQuick(app, checkOnly = false) {
  const start = Date.now();
  const read = () => app.getAXState({disableDiffing: true, emit: false});
  let state = await read(), viewedExisting = false;
  const rules = [/Value: 0, ID: id_home_tab_personal,/, /ID: id_cell_FreeCoin,|Description: 福利场(?:\s|,)/,
    /Description: 每日抽奖,/, /ID: WRUI_Pressable_MembershipLottery-LotteryButton,/];
  for (const rule of rules) {
    if (Date.now() - start > 20000 || /奖励已存入/.test(state)) break;
    if (rule === rules[0] && /Description: 福利场|id_cell_FreeCoin/.test(state)) continue;
    const rows = state.split('\n').filter(row => rule.test(row));
    if (!rows.length) continue;
    if (rows.length !== 1) break;
    if (rule === rules[2] && !/会员抽奖/.test(state)) break;
    if (rule === rules[3] && (checkOnly || !/你已中奖/.test(rows[0]))) break;
    const index = rows[0].match(/^\s*(\d+)\s/);
    if (!index) break;
    await app.click(Number(index[1]));
    if (rule === rules[3]) viewedExisting = true;
    state = await read();
  }
  return {state, viewedExisting, elapsedMs: Date.now() - start, screenshot: await app.getScreenshot({emit: false})};
}
if (typeof module !== 'undefined') module.exports = { wereadQuick };
