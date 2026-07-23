const api = require('../../utils/api')
const config = require('../../utils/config')
const { requireAuth, getConversationId, setConversationId } = require('../../utils/session')
const { markdownToHtml } = require('../../utils/markdown')
const { timeLabel, money } = require('../../utils/format')

let messageSequence = 0
const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))

function choiceFromState(state) {
  const reply = (state && (state.clarification_reply || state.clarificationReply)) || {}
  const actions = Array.isArray(reply.actions)
    ? reply.actions
        .filter(action => action && action.id && action.label && action.message)
        .map(action => ({
          id: action.id,
          label: action.label,
          message: action.message,
          recommended: Boolean(action.recommended)
        }))
    : []
  return {
    choiceKicker: reply.kicker || '',
    choiceTitle: reply.title || '',
    choicePrompt: reply.choice_prompt || reply.choicePrompt || (actions.length ? '请选择一个更接近你的答案' : ''),
    actions,
    actionSelected: ''
  }
}

function planCardFromState(state) {
  const planSaved = Boolean(state && (state.plan_saved || state.planSaved))
  if (!planSaved) return null
  const plan = (state && (state.current_plan || state.plan_draft)) || null
  if (!plan || !Array.isArray(plan.days) || !plan.days.length) return null
  const destination = plan.destination || state.entities?.destination || '本次旅行'
  return {
    title: `${destination} ${plan.days.length} 天行程`,
    destination,
    meta: `${plan.days.length} 天 · ${money(plan.total_cost, plan.currency || 'CNY')}`,
    days: plan.days.slice(0, 4).map((day, index) => ({
      dayIndex: day.day_index || index + 1,
      title: day.title || `第 ${day.day_index || index + 1} 天`,
      items: (day.items || []).slice(0, 4).map(item => item.name || item.title).filter(Boolean).join('、')
    }))
  }
}

function findSavedPlan(plans, state, conversationId) {
  const current = (state && (state.current_plan || state.plan_draft)) || {}
  const aiPlans = (plans || []).filter(item => item.planType === 'AI')
  if (current.plan_id) {
    const exact = aiPlans.find(item => item.planId === current.plan_id)
    if (exact) return exact
  }
  return aiPlans.find(item => conversationId && item.conversationId === conversationId)
}

Page({
  data: {
    input: '',
    messages: [],
    conversations: [],
    conversationId: '',
    sending: false,
    stage: '',
    stageDetail: '',
    showSessions: false,
    sessionsLoading: false,
    scrollTarget: '',
    suggestions: ['规划成都 3 天游', '查询目的地天气', '看看我的旅行偏好']
  },

  onShow() {
    if (!requireAuth()) return
    this.consumePendingPrompt()
  },

  onHide() {
    this.setData({ showSessions: false })
  },

  onUnload() {
    this._destroyed = true
  },

  async consumePendingPrompt() {
    const pending = wx.getStorageSync('oneclick_trip_pending_prompt')
    if (!pending || this.data.sending) return
    wx.removeStorageSync('oneclick_trip_pending_prompt')
    await this.sendText(pending)
  },

  onInput(event) {
    this.setData({ input: event.detail.value })
  },

  sendInput() {
    this.sendText(this.data.input)
  },

  useSuggestion(event) {
    this.sendText(event.currentTarget.dataset.text)
  },

  async ensureConversation() {
    let conversationId = this.data.conversationId || getConversationId()
    if (!conversationId) {
      const conversation = await api.createConversation()
      conversationId = conversation.conversationId
      setConversationId(conversationId)
    }
    this.setData({ conversationId })
    return conversationId
  },

  async sendText(value) {
    const text = String(value || '').trim()
    if (!text || this.data.sending) return
    const userMessage = this.createMessage('user', text)
    const assistantMessage = this.createMessage('assistant', '')
    assistantMessage.loading = true
    this.setData({
      input: '',
      sending: true,
      stage: '正在提交任务',
      stageDetail: '准备会话上下文和旅行需求',
      messages: [...this.data.messages, userMessage, assistantMessage]
    })
    this.scrollToBottom()

    try {
      const conversationId = await this.ensureConversation()
      const accepted = await api.startChat({ conversationId, message: text, ignoreUserPreferences: false })
      const runId = accepted && (accepted.run_id || accepted.runId)
      if (!runId) throw new Error('任务创建失败：没有返回任务编号')
      const response = await this.pollJob(runId)
      await this.completeAssistant(assistantMessage.id, response)
    } catch (error) {
      this.failAssistant(assistantMessage.id, error.message || '这次没有处理成功，请重试')
    } finally {
      if (!this._destroyed) {
        this.setData({ sending: false, stage: '', stageDetail: '' })
        this.scrollToBottom()
      }
    }
  },

  async pollJob(runId) {
    for (let count = 0; count < config.AI_POLL_LIMIT; count += 1) {
      const job = await api.aiJob(runId)
      if (this._destroyed) throw new Error('页面已关闭')
      this.setData({
        stage: job.stage || 'Agent 正在处理',
        stageDetail: job.detail || '正在整理本次旅行建议'
      })
      if (job.status === 'COMPLETED') {
        if (!job.response) throw new Error('任务完成，但没有返回处理结果')
        return job.response
      }
      if (job.status === 'FAILED') throw new Error(job.error || job.detail || 'AI Agent 执行失败')
      await wait(config.AI_POLL_INTERVAL)
    }
    throw new Error('处理时间较长，请稍后在当前会话中重试')
  },

  createMessage(role, text, extra = {}) {
    messageSequence += 1
    return {
      id: `message-${Date.now()}-${messageSequence}`,
      role,
      text,
      html: role === 'assistant' ? markdownToHtml(text) : '',
      loading: false,
      error: '',
      time: timeLabel(new Date()),
      savedPlan: false,
      choiceKicker: '',
      choiceTitle: '',
      choicePrompt: '',
      actions: [],
      actionSelected: '',
      planCard: null,
      planRecordId: '',
      ...extra
    }
  },

  async completeAssistant(id, response) {
    const state = response.agentState || {}
    const text = response.message || response.nextStep || '本次处理已完成。'
    const choice = choiceFromState(state)
    const planCard = planCardFromState(state)
    let planRecordId = ''
    if (state.plan_saved && planCard) {
      const plans = await api.tripPlans().catch(() => [])
      const saved = findSavedPlan(plans, state, response.conversationId || this.data.conversationId)
      planRecordId = saved ? saved.recordId : ''
    }
    const messages = this.data.messages.map(item => item.id === id ? {
      ...item,
      text,
      html: markdownToHtml(text),
      loading: false,
      savedPlan: Boolean(state.plan_saved),
      waitingConfirmation: Boolean(response.interrupted),
      planCard,
      planRecordId,
      ...choice
    } : item)
    this.setData({ messages })
  },

  chooseAction(event) {
    if (this.data.sending) return
    const { messageId, actionId, text } = event.currentTarget.dataset
    const target = this.data.messages.find(item => item.id === messageId)
    if (!target || target.actionSelected) return
    this.setData({
      messages: this.data.messages.map(item => item.id === messageId
        ? { ...item, actionSelected: actionId }
        : item)
    })
    this.sendText(text)
  },

  openSavedPlan(event) {
    const recordId = event.currentTarget.dataset.recordId
    if (!recordId) {
      this.goTrips()
      return
    }
    wx.navigateTo({ url: `/pages/trip-detail/index?id=${recordId}&type=AI` })
  },

  failAssistant(id, error) {
    const friendly = /active Agent run|409/.test(error)
      ? '上一条需求仍在处理中，请稍等几秒后再试。'
      : error
    const messages = this.data.messages.map(item => item.id === id ? {
      ...item,
      loading: false,
      error: friendly
    } : item)
    this.setData({ messages })
  },

  retryMessage(event) {
    const index = Number(event.currentTarget.dataset.index)
    const previous = this.data.messages[index - 1]
    if (previous && previous.role === 'user') this.sendText(previous.text)
  },

  goTrips() {
    wx.switchTab({ url: '/pages/trips/index' })
  },

  scrollToBottom() {
    setTimeout(() => this.setData({ scrollTarget: 'chat-bottom' }), 60)
  },

  async openSessions() {
    this.setData({ showSessions: true, sessionsLoading: true })
    try {
      const conversations = await api.conversations()
      this.setData({
        conversations: (conversations || []).map(item => ({ ...item, timeLabel: timeLabel(item.updateTime) }))
      })
    } catch (error) {
      wx.showToast({ title: error.message || '会话加载失败', icon: 'none' })
    } finally {
      this.setData({ sessionsLoading: false })
    }
  },

  closeSessions() {
    this.setData({ showSessions: false })
  },

  async newConversation() {
    if (this.data.sending) return
    try {
      const conversation = await api.createConversation()
      setConversationId(conversation.conversationId)
      this.setData({
        conversationId: conversation.conversationId,
        messages: [],
        showSessions: false
      })
    } catch (error) {
      wx.showToast({ title: error.message || '新建会话失败', icon: 'none' })
    }
  },

  async selectConversation(event) {
    if (this.data.sending) return
    const id = event.currentTarget.dataset.id
    this.setData({ sessionsLoading: true })
    try {
      const [detail, plans] = await Promise.all([
        api.conversation(id),
        api.tripPlans().catch(() => [])
      ])
      const messages = (detail.messages || []).map(message => {
        const role = message.role === 'USER' ? 'user' : 'assistant'
        const extra = { error: message.status === 'FAILED' ? message.content : '' }
        if (role === 'assistant') {
          const state = message.agentState || {}
          const saved = findSavedPlan(plans, state, id)
          Object.assign(extra, choiceFromState(state), {
            savedPlan: Boolean(state.plan_saved),
            planCard: planCardFromState(state),
            planRecordId: saved ? saved.recordId : ''
          })
        }
        return this.createMessage(role, message.content || '', extra)
      })
      messages.forEach((message, index) => {
        if (message.role !== 'assistant' || !message.actions.length) return
        const next = messages[index + 1]
        const selected = next && next.role === 'user'
          ? message.actions.find(action => action.message === next.text)
          : null
        if (selected) message.actionSelected = selected.id
      })
      setConversationId(id)
      this.setData({ conversationId: id, messages, showSessions: false })
      this.scrollToBottom()
    } catch (error) {
      wx.showToast({ title: error.message || '打开会话失败', icon: 'none' })
    } finally {
      this.setData({ sessionsLoading: false })
    }
  },

  deleteConversation(event) {
    const id = event.currentTarget.dataset.id
    wx.showModal({
      title: '删除这段会话？',
      content: '删除后将无法恢复。',
      confirmColor: '#c84c43',
      success: async result => {
        if (!result.confirm) return
        try {
          await api.deleteConversation(id)
          const conversations = this.data.conversations.filter(item => item.conversationId !== id)
          const updates = { conversations }
          if (id === this.data.conversationId) {
            setConversationId('')
            updates.conversationId = ''
            updates.messages = []
          }
          this.setData(updates)
        } catch (error) {
          wx.showToast({ title: error.message || '删除失败', icon: 'none' })
        }
      }
    })
  }
})
