export * from "./generated-contracts";

export interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  code?: string;
  message?: string;
}
