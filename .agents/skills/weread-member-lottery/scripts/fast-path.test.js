const { test } = require('node:test');
const assert = require('node:assert/strict');
const { wereadFastPath } = require('./fast-path');
const { wereadConnect } = require('./connect');
const { wereadQuick } = require('./quick-run');
const home = '7 标签 Description: 我, Value: 0, ID: id_home_tab_personal, Secondary Actions: Cancel\n45 element Description: 福利场 体验卡, Secondary Actions: Cancel';
const profile = '20 element Description: 福利, ID: id_cell_FreeCoin, Secondary Actions: Cancel';
const benefits = '12 文本 Description: 会员抽奖\n13 文本 Description: 付费会员可每日抽奖\n92 element Description: 每日抽奖, Secondary Actions: Cancel';
const lottery = label => `121 按钮 Description: ${label}, ID: WRUI_Pressable_MembershipLottery-LotteryButton, Secondary Actions: Cancel`;
const result = '4 文本 Description: 恭喜抽中书币\n5 文本 Description: 奖励已存入你的账户';
function appFor(states) {
  let position = 0;
  return {
    clicks: [],
    getAXState: async () => states[position],
    getScreenshot: async () => new Uint8Array([1]),
    getAXStateAndScreenshot: async () => ({ state: states[position] }),
    async click(index) { this.clicks.push(index); position = Math.min(position + 1, states.length - 1); },
  };
}
test('home shortcut follows fresh indices to existing result', async () => {
  const app = appFor([home, benefits, lottery('你已中奖 · 每日可抽'), result]);
  assert.equal((await wereadFastPath(app)).status, 'existing_result');
  assert.deepEqual(app.clicks, [45, 92, 121]);
});
test('shelf uses personal and benefits when shortcut absent', async () => {
  const app = appFor([home.split('\n')[0], profile, benefits, lottery('今日已抽')]);
  assert.equal((await wereadFastPath(app)).status, 'already_drawn');
  assert.deepEqual(app.clicks, [7, 20, 92]);
});
test('check-only never opens lottery result', async () => {
  const app = appFor([lottery('你已中奖 · 每日可抽')]);
  assert.equal((await wereadFastPath(app, { checkOnly: true })).status, 'already_drawn');
  assert.deepEqual(app.clicks, []);
});
test('new draw or paid label requires current policy and eligibility review', async () => {
  for (const label of ['立即抽奖', '开通会员', '10书币抽一次']) {
    const app = appFor([lottery(label)]);
    assert.equal((await wereadFastPath(app)).status, 'review_draw');
    assert.deepEqual(app.clicks, []);
  }
});
test('unchanged result page never repeats click', async () => {
  const app = appFor([lottery('你已中奖 · 每日可抽')]);
  assert.equal((await wereadFastPath(app)).status, 'result_unconfirmed');
  assert.deepEqual(app.clicks, [121]);
});
test('ambiguous entry and exhausted time budget do not click', async () => {
  const app = appFor([benefits + '\n93 element Description: 每日抽奖, Secondary Actions: Cancel']);
  assert.equal((await wereadFastPath(app)).status, 'inspect_page');
  assert.deepEqual(app.clicks, []);
  const expired = appFor([home]);
  assert.equal((await wereadFastPath(expired, { budgetMs: 0 })).status, 'time_budget');
  assert.deepEqual(expired.clicks, []);
});
test('cold start recovers using current wrapper path, not a cached path', async () => {
  const calls = [];
  const app = {};
  const api = { async getApp(path) {
    calls.push(path);
    if (calls.length === 1) throw new Error('Running application not found: com.tencent.weread');
    if (calls.length === 2) throw new Error('Ambiguous app identifier: /Applications/微信读书.app, /fresh/Wrapper/WeRead.app. Use an app name');
    return app;
  } };
  assert.equal(await wereadConnect(api), app);
  assert.deepEqual(calls, ['com.tencent.weread', 'com.tencent.weread', '/fresh/Wrapper/WeRead.app']);
});
test('connection failure is bounded', async () => {
  let calls = 0;
  await assert.rejects(wereadConnect({ async getApp() { calls++; throw new Error('Running application not found'); } }));
  assert.equal(calls, 2);
});
test('quick route uses current indices and skips personal when shortcut present', async () => {
  const app = appFor([home, benefits, lottery('你已中奖 · 每日可抽'), result]);
  assert.match((await wereadQuick(app)).state, /奖励已存入/);
  assert.deepEqual(app.clicks, [45, 92, 121]);
});
test('quick route handles shelf and never executes an unknown new draw', async () => {
  const app = appFor([home.split('\n')[0], profile, benefits, lottery('立即抽奖')]);
  assert.match((await wereadQuick(app)).state, /立即抽奖/);
  assert.deepEqual(app.clicks, [7, 20, 92]);
});
test('quick route preserves check-only, ambiguity and no-repeat boundaries', async () => {
  for (const [state, checkOnly] of [[lottery('你已中奖'), true], [lottery('10书币抽一次'), false], [home + '\n99 element Description: 福利场, Secondary Actions: Cancel', false]]) {
    const app = appFor([state]);
    await wereadQuick(app, checkOnly);
    assert.deepEqual(app.clicks, []);
  }
  const unchanged = appFor([lottery('你已中奖')]);
  await wereadQuick(unchanged);
  assert.deepEqual(unchanged.clicks, [121]);
});
