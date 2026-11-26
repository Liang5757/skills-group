import { renderToStaticMarkup, renderToString } from 'react-dom/server';
import { App } from './App.tsx';
import { defaultLocale, locales } from '../i18n/locales.ts';
import { pageMetadata } from '../lib/pageMetadata.ts';
import type { MarketPage } from '../types/page.ts';
import { defaultTheme } from '../theme/theme.ts';

export function renderPage(data: MarketPage, themeInit: string) {
  const { root, site } = data;
  const metadata = data.kind === 'skill' ? { skill: data.skill, file: data.initial.file } : undefined;
  const { title, description } = pageMetadata(locales[defaultLocale].messages, metadata);
  const asset = (name: string) => `${root}assets/${name}${site.assetQuery}`;
  // Prevent repository-controlled text from ending the raw-text script element.
  const pageData = JSON.stringify(data).replace(/</g, '\\u003c');
  const head = renderToStaticMarkup(
    <>
      <meta charSet="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <meta name="description" content={description} />
      <title>{title}</title>
      <link rel="icon" type="image/png" href={asset('favicon.png')} />
      <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      <link rel="stylesheet" href={asset('market.css')} />
    </>,
  );

  return `<!doctype html>
<html lang="${defaultLocale}" data-theme="${defaultTheme}">
<head>${head}</head>
<body>
  <div id="app">${renderToString(<App {...data} />)}</div>
  <script id="market-data" type="application/json">${pageData}</script>
  <script src="${asset('market.js')}" type="module"></script>
</body>
</html>`;
}
