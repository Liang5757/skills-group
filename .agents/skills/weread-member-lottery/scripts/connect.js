async function wereadConnect(api) {
  let lastError;
  for (let attempt = 0; attempt < 2; attempt++) {
    try { return await api.getApp('com.tencent.weread'); }
    catch (error) {
      lastError = error;
      const paths = String(error).match(/\/[^,\n]+\/Wrapper\/WeRead\.app/g) || [];
      if (paths.length === 1) return await api.getApp(paths[0].trim());
      if (!String(error).includes('Running application not found')) throw error;
    }
  }
  throw lastError;
}

if (typeof module !== 'undefined') module.exports = { wereadConnect };
