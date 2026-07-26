import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { MainTabParams } from './types';
import { RecordingStack } from './RecordingStack';
import HomeScreen from '@/screens/HomeScreen';
import ProfileScreen from '@/screens/ProfileScreen';
import { colors } from '@/theme';

const Tab = createBottomTabNavigator<MainTabParams>();

export function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.text.muted,
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarLabel: 'Analyses' }} />
      <Tab.Screen name="Record" component={RecordingStack} options={{ tabBarLabel: 'Record' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ tabBarLabel: 'Profile' }} />
    </Tab.Navigator>
  );
}
