import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach } from 'vitest'
import App from './App'
import { useAppStore } from './store'

describe('App', () => {
  beforeEach(() => {
    localStorage.clear()
    // Reset store and enable demo mode so ProtectedRoute renders children
    useAppStore.setState({
      isAuthenticated: true,
      demoMode: true,
      user: {
        id: 'test-user',
        email: 'test@example.com',
        username: 'testuser',
        displayName: 'Test User',
        isVerified: true,
      },
      token: 'test-token',
      sidebarOpen: true,
      savedAccounts: [],
      activeAccountId: null,
      messages: [],
      chatLoading: false,
    })
  })

  it('renders without crashing', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Vault')).toBeInTheDocument()
    })
  })

  it('shows chat interface by default', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('Welcome to Vault Agent')).toBeInTheDocument()
    })
  })
})
