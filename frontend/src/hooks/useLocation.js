import { useState, useEffect, useCallback } from 'react';

export function useLocation() {
  const [location, setLocation] = useState(() => {
    try {
      const saved = localStorage.getItem('agronex_location');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(() => {
    try {
      return !localStorage.getItem('agronex_location');
    } catch {
      return true;
    }
  });
  const [error, setError] = useState(null);

  const requestLocation = useCallback(() => {
    setLoading(true);
    setError(null);
    if (typeof window === 'undefined' || !navigator.geolocation) {
      const defaultLoc = {
        latitude: 11.0168,
        longitude: 76.9558,
        city: "Coimbatore",
        state: "Tamil Nadu",
        country: "India"
      };
      setLocation(defaultLoc);
      try {
        localStorage.setItem('agronex_location', JSON.stringify(defaultLoc));
      } catch {}
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const res = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`);
          const data = await res.json();
          const newLoc = {
            latitude,
            longitude,
            city: data.city || data.locality || "Your Farm",
            state: data.principalSubdivision || "",
            country: data.countryName || ""
          };
          setLocation(newLoc);
          try {
            localStorage.setItem('agronex_location', JSON.stringify(newLoc));
          } catch {}
          setLoading(false);
        } catch (err) {
          console.warn("Reverse geocode failed, using coordinates:", err);
          const fallbackLoc = {
            latitude,
            longitude,
            city: "Your Farm",
            state: "Tamil Nadu",
            country: "India"
          };
          setLocation(fallbackLoc);
          try {
            localStorage.setItem('agronex_location', JSON.stringify(fallbackLoc));
          } catch {}
          setLoading(false);
        }
      },
      (err) => {
        console.warn("Location access denied or timed out, using regional default:", err);
        const defaultLoc = {
          latitude: 11.0168,
          longitude: 76.9558,
          city: "Coimbatore",
          state: "Tamil Nadu",
          country: "India"
        };
        setLocation(defaultLoc);
        try {
          localStorage.setItem('agronex_location', JSON.stringify(defaultLoc));
        } catch {}
        setError(null);
        setLoading(false);
      },
      { timeout: 8000 }
    );
  }, []);

  useEffect(() => {
    if (location) return;
    const timer = setTimeout(() => {
      requestLocation();
    }, 0);
    return () => clearTimeout(timer);
  }, [location, requestLocation]);

  const updateLocationManually = (lat, lon, city, state, country) => {
    const newLoc = { latitude: lat, longitude: lon, city, state, country };
    setLocation(newLoc);
    try {
      localStorage.setItem('agronex_location', JSON.stringify(newLoc));
    } catch {}
  };

  return { location, loading, error, requestLocation, updateLocationManually };
}

