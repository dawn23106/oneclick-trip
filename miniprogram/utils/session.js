const TOKEN_KEY = 'oneclick_trip_token'
const USER_KEY = 'oneclick_trip_user'
const CONVERSATION_KEY = 'oneclick_trip_ai_conversation_id'

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || ''
}

function getSavedUser() {
  return wx.getStorageSync(USER_KEY) || null
}

function saveSession(loginData) {
  const user = {
    userId: loginData.userId,
    username: loginData.username,
    nickname: loginData.nickname || loginData.username,
    avatarUrl: loginData.avatarUrl || '',
    role: loginData.role
  }
  wx.setStorageSync(TOKEN_KEY, loginData.token)
  wx.setStorageSync(USER_KEY, user)
  const app = getApp()
  if (app && app.globalData) {
    app.globalData.authenticated = true
    app.globalData.user = user
  }
  return user
}

function clearSession() {
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(USER_KEY)
  wx.removeStorageSync(CONVERSATION_KEY)
  const app = getApp()
  if (app && app.globalData) {
    app.globalData.authenticated = false
    app.globalData.user = null
  }
}

function requireAuth() {
  if (getToken()) return true
  wx.reLaunch({ url: '/pages/login/index' })
  return false
}

function getConversationId() {
  return wx.getStorageSync(CONVERSATION_KEY) || ''
}

function setConversationId(conversationId) {
  if (conversationId) wx.setStorageSync(CONVERSATION_KEY, conversationId)
  else wx.removeStorageSync(CONVERSATION_KEY)
}

module.exports = {
  getToken,
  getSavedUser,
  saveSession,
  clearSession,
  requireAuth,
  getConversationId,
  setConversationId
}
