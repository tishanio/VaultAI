import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StatusBar } from 'expo-status-bar'
import { SafeAreaProvider } from 'react-native-safe-area-context'

import HomeScreen from './screens/HomeScreen'
import SubscriptionsScreen from './screens/SubscriptionsScreen'
import MarketplaceScreen from './screens/MarketplaceScreen'
import MatchDetailScreen from './screens/MatchDetailScreen'
import ProfileScreen from './screens/ProfileScreen'

const Stack = createNativeStackNavigator()
const queryClient = new QueryClient()

export default function App() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <NavigationContainer>
          <StatusBar style="light" />
          <Stack.Navigator
            screenOptions={{
              headerStyle: { backgroundColor: '#0f172a' },
              headerTintColor: '#f8fafc',
              headerTitleStyle: { fontWeight: '600' },
              contentStyle: { backgroundColor: '#020617' },
            }}
          >
            <Stack.Screen
              name="Home"
              component={HomeScreen}
              options={{ title: 'Vault' }}
            />
            <Stack.Screen
              name="Subscriptions"
              component={SubscriptionsScreen}
              options={{ title: 'My Subscriptions' }}
            />
            <Stack.Screen
              name="Marketplace"
              component={MarketplaceScreen}
              options={{ title: 'Marketplace' }}
            />
            <Stack.Screen
              name="MatchDetail"
              component={MatchDetailScreen}
              options={{ title: 'Match Details' }}
            />
            <Stack.Screen
              name="Profile"
              component={ProfileScreen}
              options={{ title: 'Profile' }}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </QueryClientProvider>
    </SafeAreaProvider>
  )
}
