export type Page<T> = { items: T[]; page: number; page_size: number; total: number };
export type Dashboard = {
  active_recalls?: number;
  blocked_lots?: number;
  completed_production_orders?: number;
  lots_in_stock?: number;
  open_alerts?: number;
  shipments_shipped?: number;
  stock_value?: string;
};
export type CostRow = {
  order_code: string; total_input_cost?: string | null; total_service_cost?: string | null; total_cost?: string | null;
  output_quantity?: string | null; ekp?: string | null; ekp_display?: string | null; vkp?: string | null;
  gross_profit_per_unit?: string | null; margin_percent?: string | null; gross_profit_total?: string | null; yield_ratio?: string | null;
};
export type Valuation = { items?: Array<{ product_code: string; product_name: string; unit_code: string; on_hand: string; value?: string | null }>; total_value?: string | null };
export type LedgerIntegrity = { consistent: boolean; mismatches?: Array<Record<string, unknown>> };
export type NotificationList = { recall_code: string; status: string; items: Array<{ customer_code: string; customer_name: string; phone?: string | null; email?: string | null; lot_code: string; quantity: string; unit_code: string; contact_status: string; contacted_at?: string | null }>; second_tier_note: string };
export type ModelSummary = Record<string, { model_version?: string; training_examples?: number; cross_validation?: Record<string, unknown>; holdout?: Record<string, unknown>; metrics?: Record<string, unknown>; note?: string; [key: string]: unknown }>;
