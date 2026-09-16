const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

// Exercise the actual skill snippet so documentation and regression tests cannot drift.
const guide = readFileSync(join(__dirname, '../references/reading-checkin.md'), 'utf8');
const snippet = guide.match(/```javascript\n([\s\S]*?)```/)[1];
const context = {};
runInNewContext(snippet.split('var initial =')[0], context);
const { pageText } = context;
const stateFor = (body, tail = '\n\t4 关闭按钮') =>
  `0 标准窗口 示例应用\n\t\t3 element ID: WRPageView, Secondary Actions: Cancel, 上一页, 下一页, Value: ${body}${tail}`;

test('retain numbered paragraphs, years and indented lists in the page anchor', () => {
  const body = '示例章节\n1 第一段\n2020 年示例\n  2 第二段\n最后一行';
  assert.equal(pageText(stateFor(body)), body);
});

test('different numbered pages with the same heading must not compare equal', () => {
  const original = '练习\n1 原页内容\n原页末尾';
  const other = '练习\n2 另一页内容\n另一页末尾';
  assert.notEqual(pageText(stateFor(original)), pageText(stateFor(other)));
});

test('stop at AX controls without including changing interface labels or indexes', () => {
  const body = '示例正文\n保留全部文字';
  for (const tail of [
    '\n\t4 关闭按钮',
    '\n\t\t12 按钮 Value: 目录, ID: reader_chapter',
    '\n\t\t20 container Secondary Actions: Cancel',
    '\n\t\t21 element ID: anotherView',
    '\n30 menu bar',
  ]) assert.equal(pageText(stateFor(body, tail)), body);
});

test('keep the last line when the page is the final AX element', () => {
  assert.equal(pageText(stateFor('示例\n3 末行', '')), '示例\n3 末行');
});

test('missing reader or missing Value cannot supply an anchor', () => {
  assert.equal(pageText('0 标准窗口 示例应用\n\t1 按钮 Description: 书架'), undefined);
  assert.equal(pageText('0 element ID: WRPageView, Secondary Actions: Cancel'), undefined);
});
