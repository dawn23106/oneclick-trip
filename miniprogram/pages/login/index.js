const api = require('../../utils/api')
const { getToken, saveSession } = require('../../utils/session')

Page({
  data: {
    mode: 'login',
    form: { username: '', password: '', nickname: '' },
    agreed: false,
    loading: false,
    error: ''
  },

  onLoad() {
    if (getToken()) wx.switchTab({ url: '/pages/home/index' })
  },

  switchMode(event) {
    this.setData({ mode: event.currentTarget.dataset.mode, error: '' })
  },

  onInput(event) {
    const field = event.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: event.detail.value, error: '' })
  },

  toggleAgreement() {
    this.setData({ agreed: !this.data.agreed, error: '' })
  },

  openLegal(event) {
    wx.navigateTo({ url: `/pages/${event.currentTarget.dataset.page}/index` })
  },

  async submit() {
    if (this.data.loading) return
    const { mode, form } = this.data
    const username = form.username.trim()
    const password = form.password
    const nickname = form.nickname.trim()
    if (!username || !password || (mode === 'register' && !nickname)) {
      this.setData({ error: '请把信息填写完整' })
      return
    }
    if (!this.data.agreed) {
      this.setData({ error: '请先阅读并同意服务条款与隐私政策' })
      return
    }
    if (mode === 'register' && (username.length < 3 || password.length < 6)) {
      this.setData({ error: '用户名至少 3 位，密码至少 6 位' })
      return
    }
    this.setData({ loading: true, error: '' })
    try {
      const data = mode === 'register'
        ? await api.register({ username, password, nickname, mobile: '' })
        : await api.login({ username, password })
      saveSession(data)
      wx.showToast({ title: mode === 'register' ? '注册成功' : '欢迎回来', icon: 'success' })
      setTimeout(() => wx.switchTab({ url: '/pages/home/index' }), 250)
    } catch (error) {
      this.setData({ error: error.message || '登录失败，请稍后重试' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
