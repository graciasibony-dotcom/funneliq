CREATE TABLE funnel_data (
    id SERIAL PRIMARY KEY,
    ad_budget INTEGER,
    num_leads INTEGER,
    leads_answered INTEGER,
    leads_not_answered INTEGER,
    followup_1 INTEGER,
    followup_2 INTEGER,
    followup_3 INTEGER,
    followup_4 INTEGER,
    followup_5 INTEGER,
    not_closed INTEGER,
    closed INTEGER,
    calls_to_closed INTEGER,
    calls_to_not_closed INTEGER,
    customer_acquisition_cost INTEGER,
    ltv_months NUMERIC,
    purchased SMALLINT,
    upsell SMALLINT,
    cumulative_profit NUMERIC,
    referred TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- Enable Row Level Security on funnel_data
ALTER TABLE funnel_data ENABLE ROW LEVEL SECURITY;

-- Allow any authenticated (logged-in) user to read all rows
DROP POLICY IF EXISTS "Authenticated users can read funnel data" ON funnel_data;

CREATE POLICY "Authenticated users can read funnel data"
ON funnel_data
FOR SELECT
TO authenticated
USING (true);