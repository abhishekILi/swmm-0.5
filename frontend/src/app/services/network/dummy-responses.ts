// Dummy fallback responses used while there is no live backend. SFD now relies on live
// CMMS/SWMM data only, so no fallback payloads are registered here.

/** Returns a dummy payload for a request path, or undefined if none is registered. */
export function getDummyResponse(_url: string): unknown | undefined {
  return undefined;
}
