import React from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from 'react-native'

const LISTINGS = [
  { id: '1', service: 'Spotify', icon: '🎵', seller: 'Alex C.', price: 4.50, distance: '2.3 km', reputation: 92, score: 84, seats: 2, reasons: ['High trust', 'Nearby'] },
  { id: '2', service: 'Google One', icon: '☁️', seller: 'Maria S.', price: 5.75, distance: '4.1 km', reputation: 88, score: 79, seats: 1, reasons: ['Good price', 'Nearby'] },
  { id: '3', service: 'YouTube Premium', icon: '📺', seller: 'James W.', price: 5.00, distance: '8.7 km', reputation: 85, score: 76, seats: 3, reasons: ['Fair price', 'Schedule match'] },
]

export default function MarketplaceScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Search Bar */}
      <View style={styles.searchBar}>
        <Text style={styles.searchPlaceholder}>🔍 Search services, sellers...</Text>
      </View>

      {/* Listings */}
      {LISTINGS.map((listing) => (
        <View key={listing.id} style={styles.card}>
          <View style={styles.cardHeader}>
            <View style={styles.iconContainer}>
              <Text style={styles.icon}>{listing.icon}</Text>
            </View>
            <View style={styles.cardInfo}>
              <Text style={styles.cardTitle}>{listing.service}</Text>
              <Text style={styles.cardSeller}>by {listing.seller}</Text>
            </View>
            <View style={styles.scoreContainer}>
              <Text style={styles.score}>{listing.score}</Text>
              <Text style={styles.scoreLabel}>match</Text>
            </View>
          </View>

          {/* Tags */}
          <View style={styles.tags}>
            {listing.reasons.map((reason, i) => (
              <View key={i} style={styles.tag}>
                <Text style={styles.tagText}>{reason}</Text>
              </View>
            ))}
          </View>

          {/* Info Row */}
          <View style={styles.infoRow}>
            <Text style={styles.infoText}>📍 {listing.distance}</Text>
            <Text style={styles.infoText}>⭐ {listing.reputation}%</Text>
            <Text style={styles.infoText}>{listing.seats} seat(s)</Text>
          </View>

          {/* Price + Action */}
          <View style={styles.priceRow}>
            <View>
              <Text style={styles.priceLabel}>Monthly Price</Text>
              <Text style={styles.price}>${listing.price.toFixed(2)}/mo</Text>
            </View>
            <TouchableOpacity style={styles.matchButton}>
              <Text style={styles.matchButtonText}>🤝 Match</Text>
            </TouchableOpacity>
          </View>
        </View>
      ))}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#020617' },
  content: { padding: 16, gap: 12 },
  searchBar: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 14,
    marginBottom: 4,
  },
  searchPlaceholder: { color: '#64748b', fontSize: 15 },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 16 },
  cardHeader: { flexDirection: 'row', alignItems: 'center' },
  iconContainer: {
    width: 48, height: 48, borderRadius: 12,
    backgroundColor: '#334155', alignItems: 'center', justifyContent: 'center',
  },
  icon: { fontSize: 24 },
  cardInfo: { flex: 1, marginLeft: 12 },
  cardTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '600' },
  cardSeller: { color: '#94a3b8', fontSize: 13, marginTop: 2 },
  scoreContainer: { alignItems: 'center' },
  score: { color: '#10b981', fontSize: 20, fontWeight: '700' },
  scoreLabel: { color: '#64748b', fontSize: 10 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 },
  tag: { backgroundColor: '#1e3a5f', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  tagText: { color: '#7dd3fc', fontSize: 12 },
  infoRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#334155',
  },
  infoText: { color: '#94a3b8', fontSize: 13 },
  priceRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 12, backgroundColor: '#0f172a', borderRadius: 10, padding: 12,
  },
  priceLabel: { color: '#64748b', fontSize: 12 },
  price: { color: '#10b981', fontSize: 20, fontWeight: '700' },
  matchButton: { backgroundColor: '#0ea5e9', borderRadius: 10, paddingHorizontal: 20, paddingVertical: 10 },
  matchButtonText: { color: '#ffffff', fontSize: 15, fontWeight: '600' },
})
