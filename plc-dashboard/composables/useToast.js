import { ref } from 'vue'

// グローバルなトースト状態
const toastState = ref({
  show: false,
  message: '',
  color: 'info',
  timeout: 3000,
  icon: ''
})

/**
 * トースト通知用コンポーザブル
 *
 * 使用例:
 * const toast = useToast()
 * toast.success('保存しました')
 * toast.error('エラーが発生しました')
 * toast.warning('警告メッセージ')
 * toast.info('情報メッセージ')
 */
export const useToast = () => {
  const show = (message, options = {}) => {
    toastState.value = {
      show: true,
      message,
      color: options.color || 'info',
      timeout: options.timeout || 3000,
      icon: options.icon || ''
    }
  }

  const success = (message, timeout = 3000) => {
    show(message, {
      color: 'success',
      timeout,
      icon: 'mdi-check-circle'
    })
  }

  const error = (message, timeout = 5000) => {
    show(message, {
      color: 'error',
      timeout,
      icon: 'mdi-alert-circle'
    })
  }

  const warning = (message, timeout = 4000) => {
    show(message, {
      color: 'warning',
      timeout,
      icon: 'mdi-alert'
    })
  }

  const info = (message, timeout = 3000) => {
    show(message, {
      color: 'info',
      timeout,
      icon: 'mdi-information'
    })
  }

  const hide = () => {
    toastState.value.show = false
  }

  return {
    state: toastState,
    show,
    success,
    error,
    warning,
    info,
    hide
  }
}
