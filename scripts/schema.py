"""Canonical value lists and the data dictionary (single source of truth).

01_generate_data.py writes data/data_dictionary.csv from TABLES below and
02_cleaning_validation.py asserts that every CSV matches it.
"""
DONOR_CATEGORIES = ["Restaurant", "Bakery", "Caterer", "Residential Society",
                    "Sweet Shop", "Canteen/Mess", "Banquet/Event Hall"]
ZONES = ["Dadar West", "Dadar East", "Shivaji Park", "Matunga", "Mahim", "Dharavi Fringe"]
FOOD_CATEGORIES = ["Cooked Meals", "Snacks & Fast Food", "Bread & Bakery", "Cakes & Pastries",
                   "Sweets & Mithai", "Packaged/Dry Food", "Fruits & Raw Produce"]
REASONS = ["Overproduction vs Demand", "Unsold at Closing/End of Day", "Near Best-Before",
           "Guest Count Lower Than Estimated", "Over-Estimation of Quantity",
           "Event Cancelled/Shortened", "Order Cancellation", "Low Footfall/Attendance",
           "Festival Over-Stocking/Celebration"]
COLLECTION_STATUSES = ["Collected - Full", "Collected - Partial", "Missed - No Volunteer Available",
                       "Missed - Arrived Beyond Safe Window", "Cancelled by Donor",
                       "Rejected - Failed Volunteer Safety Check"]
WASTE_REASONS = ["Recipient Capacity Exhausted", "No Recipient Window Within Safe Time",
                 "No Recipient Accepts Food Type/Diet", "Quality Loss During Handling"]
RECIPIENT_TYPES = ["Community Kitchen", "Night Shelter", "Children's Home", "Old-Age Home",
                   "Street Community Group", "Informal Settlement Resident Group"]
SHIFTS = ["Morning", "Afternoon", "Evening", "Late"]
PACKAGING = ["Open/Bulk Container", "Sealed Container", "Original Sealed Packet", "Boxed"]
STORAGE = ["Hot-Held", "Room Temperature", "Refrigerated"]

L = "Constant label: SYNTHETIC DEMO DATA for generated records; replace with FIELD DATA for real collection."
# (column, dtype, description, allowed values / range, nullable)
TABLES = {
 "donors": [
  ("donor_id", "string", "Primary key (D###)", "D001-D128", "No"),
  ("donor_name", "string", "Fictional donor label (no real businesses)", "free text", "No"),
  ("donor_category", "category", "Type of food donor", "; ".join(DONOR_CATEGORIES), "No"),
  ("sub_area", "category", "Study-area zone of the donor", "; ".join(ZONES), "No"),
  ("latitude", "float", "Approximate synthetic latitude (zone centroid + jitter, NOT a real address)", "18.99-19.07", "No"),
  ("longitude", "float", "Approximate synthetic longitude", "72.82-72.88", "No"),
  ("donor_size_class", "category", "Relative size within its category (tercile of typical quantity)", "Small; Medium; Large", "No"),
  ("fssai_license_declared", "category", "Donor-declared FSSAI licence/registration status (unverified)", "Yes; Pending; No; Not Applicable", "No"),
  ("onboarded_date", "date", "Date donor joined the reporting programme", "2025-11-01 to 2026-08-31", "No"),
  ("donor_status", "category", "Programme status at end of data window", "Active; Withdrawn", "No"),
  ("withdrawn_date", "date", "Date donor stopped reporting (only if Withdrawn)", "date or blank", "Yes"),
  ("reporting_channel", "category", "How the donor reports surplus", "Phone Call; Messaging Form; Walk-in Desk", "No"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
 "recipients": [
  ("recipient_id", "string", "Primary key (R##)", "R01-R25", "No"),
  ("recipient_name", "string", "Fictional organisation label - NOT a real NGO", "free text", "No"),
  ("recipient_type", "category", "Type of recipient organisation", "; ".join(RECIPIENT_TYPES), "No"),
  ("sub_area", "category", "Study-area zone", "; ".join(ZONES), "No"),
  ("latitude", "float", "Approximate synthetic latitude", "18.99-19.07", "No"),
  ("longitude", "float", "Approximate synthetic longitude", "72.82-72.88", "No"),
  ("daily_capacity_portions", "int", "Maximum portions the recipient can serve per day", "30-400", "No"),
  ("window1_start", "time", "First food-acceptance window start (HH:MM)", "HH:MM", "No"),
  ("window1_end", "time", "First window end", "HH:MM", "No"),
  ("window2_start", "time", "Second window start", "HH:MM or blank", "Yes"),
  ("window2_end", "time", "Second window end", "HH:MM or blank", "Yes"),
  ("accepts_cooked_food", "category", "Has facilities to receive cooked food", "Yes; No", "No"),
  ("diet_acceptance", "category", "Veg-only recipients cannot receive Non-Veg food", "Any; Veg-only", "No"),
  ("has_cold_storage", "category", "Has refrigeration", "Yes; No", "No"),
  ("fssai_registration_status", "category", "Synthetic declared status (real NGOs must be verified before any use)", "Declared Registered; Not Declared", "No"),
  ("verification_status", "string", "Always flags that the organisation is fictional", "SYNTHETIC - not a real organisation", "No"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
 "volunteers": [
  ("volunteer_id", "string", "Primary key (V##)", "V01-V36", "No"),
  ("volunteer_name", "string", "Fictional label", "free text", "No"),
  ("home_sub_area", "category", "Zone the volunteer starts from", "; ".join(ZONES), "No"),
  ("home_latitude", "float", "Approximate synthetic latitude", "18.99-19.07", "No"),
  ("home_longitude", "float", "Approximate synthetic longitude", "72.82-72.88", "No"),
  ("shift", "category", "Usual shift: Morning 07-14, Afternoon 13-19:30, Evening 17:30-22:30, Late 21-24", "; ".join(SHIFTS), "No"),
  ("availability_days", "category", "Days the volunteer can be rostered", "Weekdays; Weekends; All Days", "No"),
  ("vehicle_mode", "category", "Transport used for pickup and delivery", "On foot; Bicycle; Two-wheeler; Four-wheeler", "No"),
  ("max_load_kg", "float", "Maximum load per trip", "8-250", "No"),
  ("fostac_trained", "category", "Synthetic flag: completed food-handler (FoSTaC-type) training", "Yes; No", "No"),
  ("onboarded_date", "date", "Date volunteer joined", "2025-11-01 to 2026-04-30", "No"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
 "daily_context": [
  ("date", "date", "Primary key", "2025-11-01 to 2026-10-31", "No"),
  ("day_name", "category", "Weekday name", "Monday-Sunday", "No"),
  ("is_weekend", "int", "1 for Saturday/Sunday", "0; 1", "No"),
  ("festival_name", "string", "Festival window from the public 2026 calendar (moon-dependent dates +-1 day) used in the demand model", "name or No Festival", "No"),
  ("wedding_season_flag", "int", "Approximate wedding-season window flag", "0; 1", "No"),
  ("monsoon_season_flag", "int", "Monsoon window: 2026 onset ~22 Jun (IMD/press) to 30 Sep", "0; 1", "No"),
  ("rain_level", "category", "SIMULATED daily rain indicator; monthly intensity follows IMD/press reports for 2026 (not observed daily data)", "No Rain; Light/Moderate; Heavy", "No"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
 "surplus_records": [
  ("surplus_id", "string", "Primary key (S######)", "unique", "No"),
  ("donor_id", "string", "FK -> donors.donor_id", "valid donor", "No"),
  ("report_datetime", "datetime", "When the donor reported the surplus", "within data window and donor active period", "No"),
  ("prep_datetime", "datetime", "When the food was prepared/produced (donor-declared)", "<= report_datetime", "No"),
  ("food_category", "category", "Food category", "; ".join(FOOD_CATEGORIES), "No"),
  ("food_item", "string", "Specific item", "free text", "No"),
  ("diet_type", "category", "Veg / Non-Veg", "Veg; Non-Veg", "No"),
  ("quantity_kg", "float", "Reported surplus quantity in kg", "0.5-200", "No"),
  ("est_portions", "int", "Donor-estimated number of portions", ">0", "No"),
  ("portion_size_kg", "float", "Planning portion weight for the category", "0.06-0.35", "No"),
  ("surplus_reason", "category", "Reason surplus arose", "; ".join(REASONS), "No"),
  ("packaging_type", "category", "Packaging at reporting", "; ".join(PACKAGING), "Yes"),
  ("storage_condition", "category", "Holding condition at reporting", "; ".join(STORAGE), "Yes"),
  ("declared_safe_window_hours", "float", "Donor-declared hours from preparation within which food is intended to be consumed (advisory input only; humans make the safety decision)", "4-400 (cooked food 4-6 per FSSAI guidance)", "No"),
  ("perishability_class", "category", "Planning class from food category (High/Medium/Low) - NOT a safety decision", "High; Medium; Low", "No"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
 "collections": [
  ("collection_id", "string", "Primary key (C######)", "unique", "No"),
  ("surplus_id", "string", "FK -> surplus_records.surplus_id (exactly one collection-attempt record per surplus report)", "valid, unique", "No"),
  ("volunteer_id", "string", "FK -> volunteers.volunteer_id; blank if none assigned/cancelled", "valid or blank", "Yes"),
  ("assigned_datetime", "datetime", "When a volunteer was assigned", ">= report_datetime", "Yes"),
  ("pickup_datetime", "datetime", "Time of pickup (or arrival if pickup failed)", ">= assigned_datetime", "Yes"),
  ("collection_status", "category", "Outcome of the collection attempt", "; ".join(COLLECTION_STATUSES), "No"),
  ("qty_collected_kg", "float", "Kg actually collected (0 if not collected)", "0 to quantity_kg", "No"),
  ("collection_distance_km", "float", "Approx. road distance volunteer -> donor (haversine x 1.3)", "0-8", "Yes"),
  ("partial_reason", "string", "Why only part was collected", "Vehicle/Load Capacity; Donor Released Less; blank", "Yes"),
  ("rejection_reason", "string", "Volunteer-recorded reason (human judgement, logged - never automated)", "text or blank", "Yes"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
 "distributions": [
  ("distribution_id", "string", "Primary key (X######)", "unique", "No"),
  ("collection_id", "string", "FK -> collections.collection_id (1 or 2 rows per collected consignment)", "valid", "No"),
  ("recipient_id", "string", "FK -> recipients.recipient_id; blank if Not Delivered", "valid or blank", "Yes"),
  ("distribution_datetime", "datetime", "Hand-over time at recipient", ">= pickup_datetime; inside a recipient window", "Yes"),
  ("qty_distributed_kg", "float", "Kg handed over", ">= 0", "No"),
  ("beneficiaries_served", "int", "Portions served = floor(qty / portion_size_kg)", ">= 0", "No"),
  ("transport_distance_km", "float", "Approx. road distance donor -> recipient", "0-8", "Yes"),
  ("wastage_kg", "float", "Kg of the consignment not distributed (recorded on the last row of the consignment)", ">= 0", "No"),
  ("wastage_reason", "category", "Reason for wastage", "; ".join(WASTE_REASONS) + "; blank", "Yes"),
  ("distribution_status", "category", "Delivered / Not Delivered", "Delivered; Not Delivered", "No"),
  ("handover_record_complete", "category", "Hand-over record complete (donor, recipient, date, item, quantity) - record-keeping compliance proxy", "Yes; No", "No"),
  ("data_label", "string", L, "SYNTHETIC DEMO DATA", "No")],
}
