import React from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from 'react-native'
import { useNavigation } from '@react-navigation/native'

const DEMO_DATA = {
  totalSubscriptions: 5,
  monthlyCost: 80.95,
  savings: 27.50,
  activeMatches: 2,
  reputationScore: 87,
}

const QUICK_ACTIONS = [
  { label: 'Subscriptions', screen: 'Subscriptions', icon: '💳', color: '#0ea5e9' },
  { label: 'Marketplace', screen: 'Marketplace', icon: '🏪', color: '#10b981' },
  { label: 'Profile', screen: 'Profile', icon: '👤', color: '#8b5cf6' },
]

const RECENT_ACTIVITY = [
  { id: '1', text: 'New match with Alex Chen for Spotify', time: '2h ago', color: '#0ea5e9' },
  { id: '2', text: 'Escrow funded for $4.50', time: '5h ago', color: '#10b981' },
  { id: '3', text: 'Usage report generated', time: '1d ago', color: '#f59e0b' },
]

export default function HomeScreen() {
  const navigation = useNavigation()

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Welcome Banner */}
      <View style={styles.banner}>
        <Text style={styles.bannerTitle}>Welcome back 👋</Text>
        <Text style={styles.bannerSubtitle}>
          You're saving ${DEMO_DATA.savings.toFixed(2)}/month through Vault
        </Text>
      </View>

      {/* Stats Cards */}
      <View style={styles.statsGrid}>
        <View style={[styles.statCard, { borderLeftColor: '#0ea5e9' }]}>
          <Text style={styles.statLabel}>Subscriptions</Text>
          <Text style={styles.statValue}>{DEMO_DATA.totalSubscriptions}</Text>
        </View>
        <View style={[styles.statCard, { borderLeftColor: '#8b5cf6' }]}>
          <Text style={styles.statLabel}>Monthly Cost</Text>
          <Text style={styles.statValue}>${DEMO_DATA.monthlyCost}</Text>
        </View>
        <View style={[styles.statCard, { borderLeftColor: '#10b981' }]}>
          <Text style={styles.statLabel}>Savings</Text>
          <Text style={[styles.statValue, { color: '#10b981' }]}>
            ${DEMO_DATA.savings}
          </Text>
        </View>
        <View style={[styles.statCard, { borderLeftColor: '#f59e0b' }]}>
          <Text style={styles.statLabel}>Trust Score</Text>
          <Text style={styles.statValue}>{DEMO_DATA.reputationScore}%</Text>
        </View>
      </View>

      {/* Quick Actions */}
      <Text style={styles.sectionTitle}>Quick Actions</Text>
      <View style={styles.actionsRow}>
        {QUICK_ACTIONS.map((action) => (
          <TouchableOpacity
            key={action.screen}
            style={[styles.actionCard, { borderColor: action.color + '40' }]}
            onPress={() => navigation.navigate(action.screen as never)}
          >
            <Text style={styles.actionIcon}>{action.icon}</Text>
            <Text style={styles.actionLabel}>{action.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Recent Activity */}
      <Text style={styles.sectionTitle}>Recent Activity</Text>
      <View style={styles.activityList}>
        {RECENT_ACTIVITY.map((item) => (
          <View key={item.id} style={styles.activityItem}>
            <View style={[styles.activityDot, { backgroundColor: item.color }]} />
            <View style={styles.activityContent}>
              <Text style={styles.activityText}>{item.text}</Text>
              <Text style={styles.activityTime}>{item.time}</Text>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#020617' },
  content: { padding: 16, paddingBottom: 32 },
  banner: {
    backgroundColor: '#0c4a6e',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  bannerTitle: { color: '#f8fafc', fontSize: 22, fontWeight: '700' },
  bannerSubtitle: { color: '#7dd3fc', fontSize: 14, marginTop: 4 },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 20,
  },
  statCard: {
    width: '48%',
    flexGrow: 1,
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 3,
  },
  statLabel: { color: '#94a3b8', fontSize: 12 },
  statValue: { color: '#f8fafc', fontSize: 24, fontWeight: '700', marginTop: 4 },
  sectionTitle: {
    color: '#f8fafc',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    marginTop: 8,
  },
  actionsRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  actionCard: {
    flex: 1,
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
  },
  actionIcon: { fontSize: 28 },
  actionLabel: { color: '#e2e8f0', fontSize: 13, fontWeight: '500', marginTop: 8 },
  activityList: { gap: 8 },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    borderRadius: 10,
    padding: 14,
    gap: 12,
  },
  activityDot: { width: 8, height: 8, borderRadius: 4 },
  activityContent: { flex: 1 },
  activityText: { color: '#e2e8f0', fontSize: 14 },
  activityTime: { color: '#64748b', fontSize: 12, marginTop: 2 },
})
