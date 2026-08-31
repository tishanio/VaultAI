import React from 'react'
import { View, Text, ScrollView, StyleSheet } from 'react-native'

const SUBSCRIPTIONS = [
  { id: '1', name: 'Spotify', icon: '🎵', tier: 'Family', cost: 16.99, seats: '2/6', usage: 35, color: '#1DB954' },
  { id: '2', name: 'Google One', icon: '☁️', tier: 'Family', cost: 22.99, seats: '3/5', usage: 55, color: '#4285F4' },
  { id: '3', name: 'YouTube Premium', icon: '📺', tier: 'Family', cost: 22.99, seats: '1/5', usage: 15, color: '#FF0000' },
  { id: '4', name: 'Headspace', icon: '🧘', tier: 'Family', cost: 9.99, seats: '2/6', usage: 40, color: '#F47D31' },
  { id: '5', name: 'Duolingo', icon: '🦉', tier: 'Super', cost: 7.99, seats: '1/6', usage: 25, color: '#58CC02' },
]

export default function SubscriptionsScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {SUBSCRIPTIONS.map((sub) => (
        <View key={sub.id} style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>{sub.icon}</Text>
            </View>
            <View style={styles.cardInfo}>
              <Text style={styles.cardTitle}>{sub.name}</Text>
              <Text style={styles.cardSubtitle}>{sub.tier} • {sub.seats} seats</Text>
            </View>
            <View style={styles.costContainer}>
              <Text style={styles.cost}>${sub.cost}</Text>
              <Text style={styles.costPeriod}>/mo</Text>
            </View>
          </View>

          {/* Usage Bar */}
          <View style={styles.usageContainer}>
            <View style={styles.usageHeader}>
              <Text style={styles.usageLabel}>Usage</Text>
              <Text style={styles.usageValue}>{sub.usage}%</Text>
            </View>
            <View style={styles.usageBar}>
              <View
                style={[
                  styles.usageFill,
                  {
                    width: `${sub.usage}%`,
                    backgroundColor: sub.usage < 30 ? '#10b981' : sub.usage < 60 ? '#f59e0b' : '#ef4444',
                  },
                ]}
              />
            </View>
          </View>

          {sub.usage < 30 && (
            <View style={styles.savingsBanner}>
              <Text style={styles.savingsText}>
                💡 Share unused seats to save ~${(sub.cost * 0.4).toFixed(2)}/mo
              </Text>
            </View>
          )}
        </View>
      ))}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#020617' },
  content: { padding: 16, gap: 12 },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 16,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center' },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: { fontSize: 24 },
  cardInfo: { flex: 1, marginLeft: 12 },
  cardTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '600' },
  cardSubtitle: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  costContainer: { alignItems: 'flex-end' },
  cost: { color: '#f8fafc', fontSize: 18, fontWeight: '700' },
  costPeriod: { color: '#64748b', fontSize: 12 },
  usageContainer: { marginTop: 16 },
  usageHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  usageLabel: { color: '#94a3b8', fontSize: 12 },
  usageValue: { color: '#e2e8f0', fontSize: 12, fontWeight: '600' },
  usageBar: { height: 6, backgroundColor: '#334155', borderRadius: 3, overflow: 'hidden' },
  usageFill: { height: '100%', borderRadius: 3 },
  savingsBanner: {
    marginTop: 12,
    backgroundColor: '#064e3b',
    borderRadius: 8,
    padding: 10,
  },
  savingsText: { color: '#6ee7b7', fontSize: 13 },
})
