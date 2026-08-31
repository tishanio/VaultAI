import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach } from 'vitest'
import Layout from './Layout'
import { useAppStore } from '../store'

describe('Layout', () => {
  beforeEach(() => {
    localStorage.clear()
    useAppStore.setState({
      sidebarOpen: true,
      demoMode: true,
      user: null,
      token: null,
      isAuthenticated: false,
      savedAccounts: [],
      activeAccountId: null,
      messages: [],
      chatLoading: false,
    })
  })

  it('renders the Vault branding', () => {
    render(
      <MemoryRouter>
        <Layout>child</Layout>
      </MemoryRouter>
    )
    expect(screen.getByText('Vault')).toBeInTheDocument()
  })

  it('shows Agent label in header', () => {
    render(
      <MemoryRouter>
        <Layout>child</Layout>
      </MemoryRouter>
    )
    expect(screen.getByText('Agent')).toBeInTheDocument()
  })

  it('shows Demo badge when demo mode is on', () => {
    render(
      <MemoryRouter>
        <Layout>child</Layout>
      </MemoryRouter>
    )
    expect(screen.getByText('Demo')).toBeInTheDocument()
  })

  it('has dashboard and settings quick links', () => {
    render(
      <MemoryRouter>
        <Layout>child</Layout>
      </MemoryRouter>
    )
    const dashboardLink = screen.getByTitle('Dashboard')
    expect(dashboardLink).toBeInTheDocument()
    const settingsLink = screen.getByTitle('Settings')
    expect(settingsLink).toBeInTheDocument()
  })

  it('renders children', () => {
    render(
      <MemoryRouter>
        <Layout><div data-testid="child">Hello</div></Layout>
      </MemoryRouter>
    )
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })
})
