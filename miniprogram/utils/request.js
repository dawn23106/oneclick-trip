const config = require('./config')
const { getToken, clearSession } = require('./session')

let redirectingToLogin = false

function request(path, options = {}) {
  const token = getToken()
  const header = {
    'content-type': 'application/json',
    ...(options.header || {})
  }
  if (token) header.Authorization = `Bearer ${token}`

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${config.BASE_URL}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout: options.timeout || config.REQUEST_TIMEOUT,
      success(response) {
        const body = response.data || {}
        if (response.statusCode === 401) {
          clearSession()
          if (!redirectingToLogin) {
            redirectingToLogin = true
            wx.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
            setTimeout(() => {
              wx.reLaunch({
                url: '/pages/login/index',
                complete: () => { redirectingToLogin = false }
              })
            }, 500)
          }
          reject(new Error(body.message || '请先登录'))
          return
        }
        if (response.statusCode < 200 || response.statusCode >= 300 || body.success === false) {
          reject(new Error(body.message || `请求失败（${response.statusCode}）`))
          return
        }
        resolve(body.data)
      },
      fail(error) {
        const isTimeout = /timeout/i.test(error.errMsg || '')
        reject(new Error(isTimeout ? '请求超时，请稍后重试' : '无法连接服务，请检查后端和接口地址'))
      }
    })
  })
}

module.exports = request
