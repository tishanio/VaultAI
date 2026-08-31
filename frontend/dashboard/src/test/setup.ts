import '@testing-library/jest-dom'

// Polyfill ResizeObserver for jsdom (needed by recharts ResponsiveContainer)
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserverMock as any

// Suppress React Router v7 future flag warnings in tests
window.console.warn = (...args: any[]) => {
  const msg = args[0]
  if (typeof msg === 'string' && msg.includes('React Router Future Flag Warning')) return
  console.warn(...args)
}
