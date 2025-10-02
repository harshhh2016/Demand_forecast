import React, { useEffect, useRef } from 'react';

// Define the coordinates for major Indian cities (stable reference)
const MAJOR_CITIES = [
    { name: 'Delhi', position: { lat: 28.7041, lng: 77.1025 } },
    { name: 'Mumbai', position: { lat: 19.0760, lng: 72.8777 } },
    { name: 'Kolkata', position: { lat: 22.5726, lng: 88.3639 } },
    { name: 'Chennai', position: { lat: 13.0827, lng: 80.2707 } },
    { name: 'Bengaluru', position: { lat: 12.9716, lng: 77.5946 } },
    { name: 'Hyderabad', position: { lat: 17.3850, lng: 78.4867 } },
    { name: 'Ahmedabad', position: { lat: 23.0225, lng: 72.5714 } },
    { name: 'Pune', position: { lat: 18.5204, lng: 73.8567 } }
  ];

const Map = () => {
  const mapRef = useRef(null);

  useEffect(() => {
    if (window.google && mapRef.current) {
      // Coordinates for the center of India
      const centerOfIndia = { lat: 22.5937, lng: 78.9629 };
      
      const map = new window.google.maps.Map(mapRef.current, {
        zoom: 5, // A good zoom level to see the country
        center: centerOfIndia,
        disableDefaultUI: true, // Optional: Hides the default map controls for a cleaner look
      });

      // Define a custom icon for the markers
      // Using a small, simple red dot from a public domain source.
      // You can replace this URL with your own custom image if you prefer.
      const redDotIcon = {
        url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png', // A standard red pushpin icon
        // You can adjust the size if needed, but this default works well for visibility
        // size: new window.google.maps.Size(32, 32), 
        // origin: new window.google.maps.Point(0, 0),
        // anchor: new window.google.maps.Point(16, 32) // Anchor the bottom-center of the icon
      };

      // Loop through the cities and create a marker for each
      MAJOR_CITIES.forEach(city => {
        new window.google.maps.Marker({
          position: city.position,
          map: map,
          title: city.name,
          icon: redDotIcon, // Assign the custom icon here
        });
      });
    }
  }, []); 

  return <div ref={mapRef} style={{ height: '450px', width: '100%' }} className="rounded-2xl" />;
};

export default Map;