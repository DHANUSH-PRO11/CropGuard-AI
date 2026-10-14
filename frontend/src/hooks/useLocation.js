import { useState, useEffect } from 'react';

export function useLocation() {
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const savedLocation = localStorage.getItem('agronex_location');
    if (savedLocation) {
      setLocation(JSON.parse(savedLocation));
      setLoading(false);
    } else {
      requestLocation();
    }
  }, []);

  const requestLocation = () => {
    setLoading(true);
    setError(null);
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser");
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
          localStorage.setItem('agronex_location', JSON.stringify(newLoc));
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
          localStorage.setItem('agronex_location', JSON.stringify(fallbackLoc));
          setLoading(false);
        }
      },
      (err) => {
        // Fallback to regional agricultural center (Coimbatore, Tamil Nadu)
        console.warn("Location access denied or timed out, using regional default:", err);
        const defaultLoc = {
          latitude: 11.0168,
          longitude: 76.9558,
          city: "Coimbatore",
          state: "Tamil Nadu",
          country: "India"
        };
        setLocation(defaultLoc);
        localStorage.setItem('agronex_location', JSON.stringify(defaultLoc));
        setError(null);
        setLoading(false);
      },
      { timeout: 8000 }
    );
  };

  const updateLocationManually = (lat, lon, city, state, country) => {
    const newLoc = { latitude: lat, longitude: lon, city, state, country };
    setLocation(newLoc);
    localStorage.setItem('agronex_location', JSON.stringify(newLoc));
  };

  return { location, loading, error, requestLocation, updateLocationManually };
}
