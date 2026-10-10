// Kiểu tối thiểu cho Google Maps JavaScript API (02b §1.9). Không thêm `@types/google.maps` (không thêm thư viện).
// Chỉ khai phần AddressMapPicker dùng. Toạ độ chỉ nằm trong biến cục bộ của hộp thoại bản đồ, không lưu đi đâu.

export interface LatLngLiteral {
  lat: number;
  lng: number;
}

export interface GoogleLatLng {
  lat(): number;
  lng(): number;
}

export interface GoogleMapInstance {
  setCenter(center: LatLngLiteral | GoogleLatLng): void;
  setZoom(zoom: number): void;
  getCenter(): GoogleLatLng | undefined;
  addListener(event: string, handler: () => void): { remove(): void };
}

export interface GooglePlace {
  fetchFields(request: { fields: string[] }): Promise<unknown>;
  location?: GoogleLatLng | null;
  formattedAddress?: string | null;
}

export interface GooglePlacePrediction {
  text: { toString(): string };
  mainText?: { toString(): string } | null;
  secondaryText?: { toString(): string } | null;
  toPlace(): GooglePlace;
}

export interface GoogleAutocompleteSuggestion {
  placePrediction: GooglePlacePrediction | null;
}

export interface GoogleMapsNamespace {
  importLibrary(name: "maps"): Promise<{ Map: new (el: HTMLElement, options: Record<string, unknown>) => GoogleMapInstance }>;
  importLibrary(name: "places"): Promise<{
    AutocompleteSessionToken: new () => unknown;
    AutocompleteSuggestion: {
      fetchAutocompleteSuggestions(request: Record<string, unknown>): Promise<{ suggestions: GoogleAutocompleteSuggestion[] }>;
    };
  }>;
  importLibrary(name: "geocoding"): Promise<{
    Geocoder: new () => {
      geocode(request: { location: LatLngLiteral }): Promise<{ results: { formatted_address: string }[] }>;
    };
  }>;
}

export interface GoogleNs {
  maps: GoogleMapsNamespace;
}

declare global {
  interface Window {
    google?: GoogleNs;
    __caveveMapsReady?: () => void;
  }
}
