import React from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from 'react-native'

export default function MatchDetailScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Match Header */}
      <View style={styles.headerCard}>
        <Text style={styles.headerIcon}>🎵</Text>
        <Text style={styles.headerTitle}>Spotify Family</Text>
        <Text style={styles.headerSubtitle}>Match with Alex Chen</Text>
        <View style={styles.matchScoreBadge}>
          <Text style={styles.matchScoreText}>84% Match</Text>
        </View>
      </View>

      {/* Score Breakdown */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Score Breakdown</Text>
        {[
          { label: 'Trust Score', value: '92%', color: '#10b981' },
          { label: 'Proximity Score', value: '88%', color: '#0ea5e9' },
          { label: 'Schedule Score', value: '72%', color: '#f59e0b' },
        ].map((item) => (
          <View key={item.label} style={styles.scoreRow}>
            <Text style={styles.scoreLabel}>{item.label}</Text>
            <View style={styles.scoreBarContainer}>
              <View style={[styles.scoreBarFill, { width: item.value, backgroundColor: item.color }]} />
            </View>
            <Text style={[styles.scoreValue, { color: item.color }]}>{item.value}</Text>
          </View>
        ))}
      </View>

      {/* Match Details */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Details</Text>
        {[
          { icon: '💰', label: 'Monthly Price', value: '$4.50/mo' },
          { icon: '📍', label: 'Distance', value: '2.3 km away' },
          { icon: '⭐', label: 'Seller Rating', value: '92% positive' },
          { icon: '🗓', label: 'Status', value: 'Accepted' },
        ].map((item) => (
          <View key={item.label} style={styles.detailRow}>
            <Text style={styles.detailIcon}>{item.icon}</Text>
            <Text style={styles.detailLabel}>{item.label}</Text>
            <Text style={styles.detailValue}>{item.value}</Text>
          </View>
        ))}
      </View>

      {/* Escrow Info */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Payment (Escrow)</Text>
        <View style={styles.escrowBanner}>
          <Text style={styles.escrowIcon}>🔒</Text>
          <View style={styles.escrowInfo}>
            <Text style={styles.escrowTitle}>Funds Protected</Text>
            <Text style={styles.escrowSubtitle}>
              Your payment is held securely in escrow until the seller confirms delivery.
            </Text>
          </View>
        </View>
      </View>

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity style={styles.acceptButton}>
          <Text style={styles.acceptButtonText}>✅ Accept Match</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.declineButton}>
          <Text style={styles.declineButtonText}>Decline</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#020617' },
  content: { padding: 16, gap: 12, paddingBottom: 32 },
  headerCard: {
    backgroundColor: '#0c4a6e', borderRadius: 16, padding: 24,
    alignItems: 'center',
  },
  headerIcon: { fontSize: 48 },
  headerTitle: { color: '#f8fafc', fontSize: 22, fontWeight: '700', marginTop: 8 },
  headerSubtitle: { color: '#7dd3fc', fontSize: 15, marginTop: 4 },
  matchScoreBadge: {
    backgroundColor: '#10b981', borderRadius: 20, paddingHorizontal: 16,
    paddingVertical: 6, marginTop: 12,
  },
  matchScoreText: { color: '#ffffff', fontSize: 14, fontWeight: '700' },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 16 },
  sectionTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '600', marginBottom: 12 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  scoreLabel: { color: '#94a3b8', fontSize: 13, width: 120 },
  scoreBarContainer: { flex: 1, height: 6, backgroundColor: '#334155', borderRadius: 3, marginHorizontal: 8 },
  scoreBarFill: { height: '100%', borderRadius: 3 },
  scoreValue: { fontSize: 13, fontWeight: '600', width: 40, textAlign: 'right' },
  detailRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  detailIcon: { fontSize: 18, width: 30 },
  detailLabel: { color: '#94a3b8', fontSize: 14, flex: 1 },
  detailValue: { color: '#f8fafc', fontSize: 14, fontWeight: '500' },
  escrowBanner: { flexDirection: 'row', backgroundColor: '#064e3b', borderRadius: 10, padding: 14, gap: 12 },
  escrowIcon: { fontSize: 28 },
  escrowInfo: { flex: 1 },
  escrowTitle: { color: '#6ee7b7', fontSize: 14, fontWeight: '600' },
  escrowSubtitle: { color: '#a7f3d0', fontSize: 13, marginTop: 2 },
  actions: { gap: 10 },
  acceptButton: { backgroundColor: '#10b981', borderRadius: 12, padding: 16, alignItems: 'center' },
  acceptButtonText: { color: '#ffffff', fontSize: 16, fontWeight: '600' },
  declineButton: { backgroundColor: '#334155', borderRadius: 12, padding: 16, alignItems: 'center' },
  declineButtonText: { color: '#94a3b8', fontSize: 16, fontWeight: '500' },
})
