/**
 * NEXUS IMS — Global app state (Zustand)
 */
import { create } from 'zustand';

interface AppState {
  tenantId: string | null;
  warehouseId: string | null;
  setTenant: (id: string | null) => void;
  setWarehouse: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  tenantId: null,
  warehouseId: null,
  setTenant: (id) => set({ tenantId: id }),
  setWarehouse: (id) => set({ warehouseId: id }),
}));
