const { getToken, getSavedUser } = require('./utils/session')

App({
  globalData: {
    authenticated: Boolean(getToken()),
    user: getSavedUser()
  },

  onLaunch() {
    this.globalData.authenticated = Boolean(getToken())
    this.globalData.user = getSavedUser()
  }
})
