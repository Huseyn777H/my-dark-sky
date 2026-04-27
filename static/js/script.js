document.addEventListener("DOMContentLoaded", () => {
    const useLocationButton = document.getElementById("use-location");

    if (!useLocationButton) {
        return;
    }

    useLocationButton.addEventListener("click", () => {
        if (!navigator.geolocation) {
            window.alert("Geolocation is not supported in this browser.");
            return;
        }

        useLocationButton.disabled = true;
        useLocationButton.textContent = "Locating...";

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                window.location.href = `/?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
            },
            () => {
                useLocationButton.disabled = false;
                useLocationButton.textContent = "Use Current Location";
                window.alert("Unable to read your location. You can still search for a city manually.");
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000,
            }
        );
    });
});
