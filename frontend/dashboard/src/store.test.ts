import { describe, it, expect, beforeEach } from 'vitest'
import { useAppStore, type User } from './store'

const mockUser: User = {
  id: 'u1',
  email: 'test@example.com',
  username: 'testuser',
  displayName: 'Test User',
  isVerified: true,
  reputationScore: 0.8,
}

const mockUser2: User = {
  id: 'u2',
  email: 'other@example.com',
  username: 'otheruser',
  displayName: 'Other User',
  isVerified: true,
  reputationScore: 0.9,
}

describe('useAppStore', () => {
  beforeEach(() => {
    localStorage.clear()
    useAppStore.setState({
      sidebarOpen: true,
      demoMode: false,
      user: null,
      token: null,
      isAuthenticated: false,
      savedAccounts: [],
      activeAccountId: null,
    })
  })

  it('has initial state', () => {
    const state = useAppStore.getState()
    expect(state.sidebarOpen).toBe(true)
    expect(state.demoMode).toBe(false)
  })

  it('toggles sidebar', () => {
    const { toggleSidebar } = useAppStore.getState()
    toggleSidebar()
    expect(useAppStore.getState().sidebarOpen).toBe(false)
    toggleSidebar()
    expect(useAppStore.getState().sidebarOpen).toBe(true)
  })

  it('toggles demo mode', () => {
    const { toggleDemoMode } = useAppStore.getState()
    toggleDemoMode()
    expect(useAppStore.getState().demoMode).toBe(true)
    toggleDemoMode()
    expect(useAppStore.getState().demoMode).toBe(false)
  })

  describe('multi-account', () => {
    it('adds an account', () => {
      const { addAccount } = useAppStore.getState()
      addAccount(mockUser, 'token-1')

      const state = useAppStore.getState()
      expect(state.savedAccounts).toHaveLength(1)
      expect(state.savedAccounts[0].user.email).toBe('test@example.com')
      expect(state.activeAccountId).toBe(state.savedAccounts[0].id)
      expect(state.isAuthenticated).toBe(true)
      expect(state.user?.email).toBe('test@example.com')
    })

    it('adds multiple accounts and switches', () => {
      const { addAccount } = useAppStore.getState()
      addAccount(mockUser, 'token-1')
      addAccount(mockUser2, 'token-2')

      const state = useAppStore.getState()
      expect(state.savedAccounts).toHaveLength(2)
      expect(state.activeAccountId).toBe(state.savedAccounts[1].id)

      // Switch to first account
      const { switchAccount } = useAppStore.getState()
      switchAccount(state.savedAccounts[0].id)

      const switched = useAppStore.getState()
      expect(switched.activeAccountId).toBe(state.savedAccounts[0].id)
      expect(switched.user?.email).toBe('test@example.com')
    })

    it('removes an account', () => {
      const { addAccount } = useAppStore.getState()
      addAccount(mockUser, 'token-1')
      addAccount(mockUser2, 'token-2')

      const { removeAccount, savedAccounts } = useAppStore.getState()
      removeAccount(savedAccounts[0].id)

      const state = useAppStore.getState()
      expect(state.savedAccounts).toHaveLength(1)
      expect(state.user?.email).toBe('other@example.com')
    })

    it('removes the active account and switches to next', () => {
      const { addAccount } = useAppStore.getState()
      addAccount(mockUser, 'token-1')
      addAccount(mockUser2, 'token-2')

      // Switch to first account
      const { savedAccounts, switchAccount } = useAppStore.getState()
      switchAccount(savedAccounts[0].id)

      // Remove the active account
      const { removeAccount } = useAppStore.getState()
      removeAccount(savedAccounts[0].id)

      const state = useAppStore.getState()
      expect(state.user?.email).toBe('other@example.com')
      expect(state.isAuthenticated).toBe(true)
    })

    it('removes all accounts results in logged out state', () => {
      const { addAccount } = useAppStore.getState()
      addAccount(mockUser, 'token-1')

      const { savedAccounts: accs, removeAccount } = useAppStore.getState()
      removeAccount(accs[0].id)

      const state = useAppStore.getState()
      expect(state.savedAccounts).toHaveLength(0)
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
    })

    it('persists accounts to localStorage', () => {
      const { addAccount } = useAppStore.getState()
      addAccount(mockUser, 'token-1')

      const raw = localStorage.getItem('vault_saved_accounts')
      expect(raw).toBeTruthy()
      const parsed = JSON.parse(raw!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].user.email).toBe('test@example.com')
    })
  })
})
