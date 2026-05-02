import { create } from 'zustand'

interface Toast {
  id: string
  message: string
  type: 'error' | 'success' | 'info'
}

interface UIState {
  toasts: Toast[]
  pageLoading: boolean

  addToast: (message: string, type?: 'error' | 'success' | 'info') => void
  removeToast: (id: string) => void
  setPageLoading: (loading: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  toasts: [],
  pageLoading: false,

  addToast: (message, type = 'info') => {
    const id = Date.now().toString()
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }))
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, 4000)
  },

  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  setPageLoading: (pageLoading) => set({ pageLoading }),
}))
