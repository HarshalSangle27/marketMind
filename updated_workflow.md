# MarketMind Workflow Diagram

Here is the revised diagram. I've strictly aligned the paths to reflect the exact loops, branches, and specific column layout behaviors present in the actual image (e.g. the update loops, valid-data cycles, and right-column jumping), while injecting the new responsive homepage logic explicitly!

```mermaid
flowchart TD
    classDef startend fill:#00C896,stroke:#000,stroke-width:2px,color:#000
    classDef process fill:#4A90E2,stroke:#000,stroke-width:2px,color:#FFF
    classDef decision fill:#FFF,stroke:#FF0000,stroke-width:2px,color:#000

    %% Left Main Column Sequence
    Start([Start]):::startend --> VisitPage["Visit Homepage"]:::process
    
    %% New Logic Injected into the core flow
    VisitPage --> LoginCheck1{"Logged In?"}:::decision
    LoginCheck1 -- No --> GuestHome["<b>Guest View</b><br/>Search Bar, Trending Stocks<br/>Top News, AI Tools & Insights"]:::process
    LoginCheck1 -- Yes --> UserHome["<b>User View</b><br/>Search Bar, Recent Stocks<br/>Top News, AI Tools & Insights"]:::process
    
    GuestHome --> InputTicker["Input Ticker<br/>(e.g. RELIANCE)"]:::process
    UserHome --> InputTicker
    
    InputTicker --> ValidData{"Valid Data?"}:::decision
    
    %% Right-side error loop (just like the red No line in image)
    ValidData -- No --> FlashError["Flash Error:<br/>'Not Found'"]:::process
    FlashError --> InputTicker
    
    %% Core success flow
    ValidData -- Yes --> LoadDashboard["Load Dashboard<br/>(Price, Vol, High/Low)"]:::process
    LoadDashboard --> RenderChart["Render Chart"]:::process
    
    %% Side interaction loops
    RenderChart --> UseSIP["Use SIP Sliders"]:::process
    UseSIP --> UpdatePie["Update Pie Chart"]:::process
    UpdatePie --> LoadDashboard
    
    %% Progression to AI tool
    RenderChart --> ClickAI["Click 'AI Forecast'?"]:::process
    ClickAI --> ForecastLoginCheck{"Logged In?"}:::decision
    
    %% Path termination
    ForecastLoginCheck -- No --> GoLogin["Go to login"]:::process
    
    %% Jump to Right Column
    ForecastLoginCheck -- Yes -----> AIModelBox
    
    %% Right AI Model Side
    subgraph AIModelBox[ ]
        direction LR
        Regression["Regression"]:::process
        News["News"]:::process
    end
    
    AIModelBox --> FinalVerdict["Final Verdict<br/>(Buy/Sell)"]:::process
    FinalVerdict --> ShowPrediction["Show Prediction"]:::process
    ShowPrediction --> SubscribeCheck{"Subscribe?"}:::decision
    
    SubscribeCheck -- Yes --> SaveEmail["Save & Send Email"]:::process
    SaveEmail --> EndNode([End]):::startend
    
    %% Direct skip to end (like the red No line in image)
    SubscribeCheck -- No ----> EndNode
    
    %% Styling the AI Box explicitly
    style AIModelBox fill:transparent,stroke:#000,stroke-width:2px
```
