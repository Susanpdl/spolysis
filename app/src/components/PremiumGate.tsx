import React from 'react';
import { useSubscription } from '@/hooks/useSubscription';

interface PremiumGateProps {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

export function PremiumGate({ children, fallback }: PremiumGateProps) {
  const { isPremium } = useSubscription();
  return <>{isPremium ? children : fallback}</>;
}
