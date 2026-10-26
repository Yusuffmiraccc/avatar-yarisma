export function visibleCostFields(fields: string[], allowed: boolean) {
  return allowed ? fields : fields.filter((field) => !/(cost|ekp|vkp|margin|profit|value|price)/i.test(field));
}
