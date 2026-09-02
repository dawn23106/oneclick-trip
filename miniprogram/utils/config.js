// 体验版和正式版固定使用已备案的 HTTPS 域名。开发版可在调试控制台执行：
// wx.setStorageSync('apiBaseUrl', 'http://127.0.0.1:18080')
// 真机调试时把地址替换为电脑的局域网 IP。
const accountInfo = wx.getAccountInfoSync ? wx.getAccountInfoSync() : null
const envVersion = accountInfo && accountInfo.miniProgram
  ? accountInfo.miniProgram.envVersion
  : 'develop'
const storedBaseUrl = wx.getStorageSync ? wx.getStorageSync('apiBaseUrl') : ''

module.exports = {
  BASE_URL: envVersion === 'develop'
    ? (storedBaseUrl || 'http://127.0.0.1:18080')
    : 'https://api-trip.yjzdev.cn',
  REQUEST_TIMEOUT: 60000,
  AI_POLL_INTERVAL: 900,
  AI_POLL_LIMIT: 400
}
