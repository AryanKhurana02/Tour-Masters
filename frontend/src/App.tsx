import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { ItineraryPage } from "./pages/ItineraryPage";
import { PlacePage } from "./pages/PlacePage";
import { ResultsPage } from "./pages/ResultsPage";
import { SavedTripDetailPage } from "./pages/SavedTripDetailPage";
import { SavedTripsPage } from "./pages/SavedTripsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="plan" element={<HomePage />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="place/:id" element={<PlacePage />} />
          <Route path="itinerary" element={<ItineraryPage />} />
          <Route path="saved" element={<SavedTripsPage />} />
          <Route path="saved/:id" element={<SavedTripDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
