import type { UnavailableReason } from '../../types/preview.ts';
import type { Theme } from '../../theme/theme.ts';

const messages = {
  header: {
    skip: '跳到主要内容',
    home: 'Skills Group 首页',
    navigation: '主导航',
    market: '技能市场',
  },
  catalog: {
    description: '发现、预览和安装可复用的 Agent 技能。',
    metaDescription: '浏览 Skills Group 的技能，预览说明并按需安装。',
    all: '全部技能',
    search: '搜索技能名称或描述',
    count: (count: number) => `${count} 个`,
    noResults: '没有找到匹配的技能。',
    empty: '暂无技能。',
    clearSearch: '清除搜索',
    viewSkill: '查看详情',
  },
  pagination: {
    navigation: '技能列表分页',
    previous: '上一页',
    next: '下一页',
    page: (page: number, total: number) => `第 ${page} / ${total} 页`,
    jumpTo: '跳至',
    pageNumber: '跳至页码',
    jump: '跳转',
  },
  detail: {
    navigation: '页面导航',
    versionMissing: '版本未标注',
    source: '技能来源',
    toggleFiles: '展开或收起技能文件',
    expandFiles: '展开技能文件',
    collapseFiles: '收起技能文件',
    directory: '文件目录',
    files: '技能文件',
    viewMode: 'Markdown 查看方式',
    preview: '预览',
    code: '源码',
    viewOnGitHub: '在 GitHub 查看',
    opened: (path: string) => `已打开 ${path}`,
    unavailable: {
      tooLarge: '文件较大，可在 GitHub 上查看。',
      unsupported: '此文件格式可在 GitHub 上查看。',
    } satisfies Record<UnavailableReason, string>,
  },
  install: {
    title: '安装指引',
    requirement: '需要 Node.js 22.20 或更新版本',
    copy: '复制命令',
    copied: { label: '已复制', message: '安装命令已复制' },
    manual: { label: '请手动复制', message: '安装命令已选中，请手动复制' },
  },
  preferences: {
    label: '界面设置',
    language: '界面语言',
    darkMode: '深色模式',
    switchTheme: (theme: string) => `切换到${theme}模式`,
    themes: { dark: '深色', light: '浅色' } satisfies Record<Theme, string>,
  },
};

export default messages;
