import React from 'react'
import { View, Text, ScrollView, StyleSheet } from 'react-native'

export default function ProfileScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Profile Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>V</Text>
        </View>
        <Text style={styles.name}>Demo User</Text>
        <Text style={styles.email}>demo@vault.app</Text>
        <View style={styles.tierBadge}>
          <Text style={styles.tierText}>⭐ Gold Tier</Text>
        </View>
      </View>

      {/* Reputation Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Reputation Score</Text>
        <View style={styles.reputationCircle}>
          <Text style={styles.reputationValue}>87%</Text>
          <Text style={styles.reputationLabel}>Overall</Text>
        </View>
        <View style={styles.scoreDetails}>
          {[
            { label: 'Reliability', value: '90%' },
            { label: 'Communication', value: '82%' },
            { label: 'Payment', value: '88%' },
          ].map((item) => (
            <View key={item.label} style={styles.scoreRow}>
              <Text style={styles.scoreLabel}>{item.label}</Text>
              <Text style={styles.scoreValue}>{item.value}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Stats */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Activity Stats</Text>
        <View style={styles.statsGrid}>
          {[
            { label: 'Transactions', value: '12' },
            { label: 'Positive Reviews', value: '11' },
            { label: 'KYC Verified', value: '✓' },
          ].map((item) => (
            <View key={item.label} style={styles.statItem}>
              <Text style={styles.statValue}>{item.value}</Text>
              <Text style={styles.statLabel}>{item.label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Settings Links */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Account Settings</Text>
        {['Edit Profile', 'Notifications', 'Security', 'Privacy', 'Sign Out'].map((item) => (
          <View key={item} style={styles.settingRow}>
            <Text style={styles.settingText}>{item}</Text>
            <Text style={styles.settingArrow}>›</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#020617' },
  content: { padding: 16, gap: 12, paddingBottom: 32 },
  header: { alignItems: 'center', backgroundColor: '#1e293b', borderRadius: 16, padding: 24 },
  avatar: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: '#0ea5e9', alignItems: 'center', justifyContent: 'center',
  },
  avatarText: { color: '#ffffff', fontSize: 32, fontWeight: '700' },
  name: { color: '#f8fafc', fontSize: 22, fontWeight: '700', marginTop: 12 },
  email: { color: '#94a3b8', fontSize: 14, marginTop: 4 },
  tierBadge: {
    backgroundColor: '#f59e0b30', borderRadius: 20,
    paddingHorizontal: 14, paddingVertical: 6, marginTop: 10,
  },
  tierText: { color: '#fbbf24', fontSize: 14, fontWeight: '600' },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 16 },
  sectionTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '600', marginBottom: 12 },
  reputationCircle: { alignItems: 'center', marginBottom: 16 },
  reputationValue: { color: '#10b981', fontSize: 48, fontWeight: '700' },
  reputationLabel: { color: '#94a3b8', fontSize: 14 },
  scoreDetails: { gap: 8 },
  scoreRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#334155' },
  scoreLabel: { color: '#94a3b8', fontSize: 14 },
  scoreValue: { color: '#f8fafc', fontSize: 14, fontWeight: '600' },
  statsGrid: { flexDirection: 'row', justifyContent: 'space-around' },
  statItem: { alignItems: 'center' },
  statValue: { color: '#f8fafc', fontSize: 24, fontWeight: '700' },
  statLabel: { color: '#94a3b8', fontSize: 12, marginTop: 4 },
  settingRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  settingText: { color: '#e2e8f0', fontSize: 15 },
  settingArrow: { color: '#64748b', fontSize: 20 },
})
