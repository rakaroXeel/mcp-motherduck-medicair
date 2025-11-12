class L1Category(str, Enum):
    programming_languages = "programming_languages"
    frameworks_libraries  = "frameworks_libraries"
    ai_ml                 = "ai_ml"
    cloud                 = "cloud"
    devops                = "devops"
    testing_quality       = "testing_quality"
    databases_storage     = "databases_storage"
    data_eng_analytics    = "data_eng_analytics"
    frontend              = "frontend"
    backend               = "backend"
    mobile                = "mobile"
    security              = "security"
    tooling_methodology   = "tooling_methodology"
    other                 = "other"

class L2Category(str, Enum):
    # linguaggi
    lang_backend   = "lang_backend"
    lang_frontend  = "lang_frontend"
    lang_mobile    = "lang_mobile"
    lang_scripting = "lang_scripting"
    lang_systems   = "lang_systems"
    lang_data_sci  = "lang_data_sci"
    # framework/lib
    fw_web_backend = "fw_web_backend"
    fw_web_frontend= "fw_web_frontend"
    fw_mobile      = "fw_mobile"
    fw_data        = "fw_data"
    fw_ml          = "fw_ml"
    fw_test        = "fw_test"
    # ai/ml
    ml_lib         = "ml_lib"
    dl_lib         = "dl_lib"
    llm_nlp        = "llm_nlp"
    mlops          = "mlops"
    feature_eng    = "feature_eng"
    # cloud
    cloud_aws      = "cloud_aws"
    cloud_azure    = "cloud_azure"
    cloud_gcp      = "cloud_gcp"
    cloud_serverless = "cloud_serverless"
    cloud_data     = "cloud_data"
    # devops
    containers     = "containers"
    orchestration  = "orchestration"
    iac            = "iac"
    ci_cd          = "ci_cd"
    monitoring_obs = "monitoring_obs"
    platform_eng   = "platform_eng"
    # testing
    test_unit      = "test_unit"
    test_e2e       = "test_e2e"
    test_perf      = "test_perf"
    test_sec       = "test_sec"
    # database/storage
    db_relational  = "db_relational"
    db_nosql_doc   = "db_nosql_doc"
    db_kv          = "db_kv"
    db_columnar    = "db_columnar"
    db_graph       = "db_graph"
    db_time_series = "db_time_series"
    warehouse      = "warehouse"
    lakehouse      = "lakehouse"
    search_queue_stream = "search_queue_stream"
    # data eng/analytics
    etl_orch       = "etl_orch"
    transform_dbt  = "transform_dbt"
    streaming      = "streaming"
    bi_tools       = "bi_tools"
    data_gov_cat   = "data_gov_cat"
    # frontend/backend/mobile/security/tooling
    fe_ui_runtime  = "fe_ui_runtime"
    fe_state_mgmt  = "fe_state_mgmt"
    fe_build_tools = "fe_build_tools"
    fe_css_tooling = "fe_css_tooling"
    be_runtime     = "be_runtime"
    be_micro_api   = "be_micro_api"
    be_messaging   = "be_messaging"
    mobile_ios     = "mobile_ios"
    mobile_android = "mobile_android"
    mobile_xplat   = "mobile_xplat"
    appsec         = "appsec"
    cloudsec       = "cloudsec"
    iam            = "iam"
    vcs            = "vcs"
    proj_mgmt      = "proj_mgmt"
    agile_scrum    = "agile_scrum"
    design_systems = "design_systems"
    other          = "other"

class SkillTag(BaseModel):
    l1: L1Category
    l2: L2Category = L2Category.other
    l3: str        = Field(description="Tecnologia/skill canonica, o 'other'")
    vendor_family: Optional[str] = None
    version: Optional[str] = None
    canonical_id: Optional[str] = None
    weight: float = 1.0

class JobSkillTags(BaseModel):
    doc_id: str
    source_platform: str = "linkedin"
    source_url: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location_text: Optional[str] = None
    seniority_hint: Optional[str] = None
    skills: List[SkillTag]
 