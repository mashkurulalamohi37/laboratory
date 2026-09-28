import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type CartItemType = "TEST" | "PACKAGE";
export type BookingModeType = "HOME" | "CENTRE";

export interface CartItem {
  id: string; // item id (test id or package id)
  type: CartItemType;
  name: string;
  slug?: string;
  price: number; // in poisha
  mrp?: number; // in poisha
  tatHours?: number;
  preparation?: string | null;
  homeCollectionEligible?: boolean;
  patientId?: string | null;
  patientName?: string | null;
}

interface CartContextValue {
  items: CartItem[];
  itemCount: number;
  subtotal: number; // in poisha
  mode: BookingModeType;
  selectedCentreId: string | null;
  selectedAddressId: string | null;
  selectedSlotId: string | null;
  couponCode: string | null;
  addItem: (item: Omit<CartItem, "patientId" | "patientName">) => void;
  removeItem: (id: string) => void;
  assignPatient: (itemId: string, patientId: string, patientName: string) => void;
  assignAllPatients: (patientId: string, patientName: string) => void;
  setMode: (mode: BookingModeType) => void;
  setSelectedCentreId: (id: string | null) => void;
  setSelectedAddressId: (id: string | null) => void;
  setSelectedSlotId: (id: string | null) => void;
  setCouponCode: (code: string | null) => void;
  hasItem: (id: string) => boolean;
  clearCart: () => void;
}

const STORAGE_KEY = "nirnoy_cart_v1";

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [mode, setMode] = useState<BookingModeType>("HOME");
  const [selectedCentreId, setSelectedCentreId] = useState<string | null>(null);
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(null);
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [couponCode, setCouponCode] = useState<string | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Ignore storage errors
    }
  }, [items]);

  const addItem = (item: Omit<CartItem, "patientId" | "patientName">) => {
    setItems((prev) => {
      if (prev.some((i) => i.id === item.id)) {
        return prev;
      }
      return [...prev, { ...item, patientId: null, patientName: null }];
    });
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const assignPatient = (itemId: string, patientId: string, patientName: string) => {
    setItems((prev) =>
      prev.map((i) => (i.id === itemId ? { ...i, patientId, patientName } : i))
    );
  };

  const assignAllPatients = (patientId: string, patientName: string) => {
    setItems((prev) =>
      prev.map((i) => ({ ...i, patientId, patientName }))
    );
  };

  const hasItem = (id: string) => items.some((i) => i.id === id);

  const clearCart = () => {
    setItems([]);
    setSelectedSlotId(null);
    setCouponCode(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  };

  const subtotal = useMemo(
    () => items.reduce((acc, curr) => acc + (curr.price || 0), 0),
    [items]
  );

  const value = useMemo(
    () => ({
      items,
      itemCount: items.length,
      subtotal,
      mode,
      selectedCentreId,
      selectedAddressId,
      selectedSlotId,
      couponCode,
      addItem,
      removeItem,
      assignPatient,
      assignAllPatients,
      setMode,
      setSelectedCentreId,
      setSelectedAddressId,
      setSelectedSlotId,
      setCouponCode,
      hasItem,
      clearCart,
    }),
    [items, subtotal, mode, selectedCentreId, selectedAddressId, selectedSlotId, couponCode]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return ctx;
}
