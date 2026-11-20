// Read at build time from the CMS export; LegacyMap is enabled for some stores.
export const enabledWidgets: string[] = JSON.parse(process.env.NEXT_PUBLIC_WIDGETS ?? '["RevenueChart"]');
