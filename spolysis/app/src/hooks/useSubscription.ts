import { useState, useEffect } from 'react';
import Purchases, { CustomerInfo } from 'react-native-purchases';

export function useSubscription() {
  const [isPremium, setIsPremium] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Purchases.getCustomerInfo()
      .then((info: CustomerInfo) => {
        setIsPremium(info.entitlements.active['premium'] !== undefined);
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  }, []);

  const purchasePremium = async (packageId: string) => {
    const offerings = await Purchases.getOfferings();
    const pkg = offerings.current?.availablePackages.find(
      (p) => p.identifier === packageId,
    );
    if (!pkg) throw new Error('Package not found');
    await Purchases.purchasePackage(pkg);
    setIsPremium(true);
  };

  const restorePurchases = async () => {
    const info = await Purchases.restorePurchases();
    setIsPremium(info.entitlements.active['premium'] !== undefined);
  };

  return { isPremium, isLoading, purchasePremium, restorePurchases };
}
