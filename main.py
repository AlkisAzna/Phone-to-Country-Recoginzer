import os
import logging
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import phonenumbers
from phonenumbers import NumberParseException
import pycountry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("API_TOKEN", "dev-token-change-in-production")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app = FastAPI(
    title="Phone Number Lookup API",
    description="Phone number validation with country origin information",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PhoneNumberInfo(BaseModel):
    phone_number: str
    country_code: str
    country_name: str
    country_region: Optional[str] = None
    number_type: str
    is_valid: bool
    is_possible: bool
    formatted_e164: str
    formatted_national: str
    timezone: Optional[str] = None


class ValidationResult(BaseModel):
    phone: str
    is_valid: bool
    is_possible: bool
    country_code: Optional[str] = None
    error: Optional[str] = None


class CountryInfo(BaseModel):
    name: str
    alpha_2: str
    alpha_3: str
    numeric: str


class CountriesResponse(BaseModel):
    total: int
    countries: list[CountryInfo]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    api_token_configured: bool


_NUMBER_TYPE_MAPPING: Dict[int, str] = {
    phonenumbers.PhoneNumberType.MOBILE: "MOBILE",
    phonenumbers.PhoneNumberType.FIXED_LINE: "FIXED_LINE",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
    phonenumbers.PhoneNumberType.TOLL_FREE: "TOLL_FREE",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "PREMIUM_RATE",
    phonenumbers.PhoneNumberType.SHARED_COST: "SHARED_COST",
    phonenumbers.PhoneNumberType.VOIP: "VOIP",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "PERSONAL_NUMBER",
    phonenumbers.PhoneNumberType.PAGER: "PAGER",
    phonenumbers.PhoneNumberType.UAN: "UAN",
    phonenumbers.PhoneNumberType.UNKNOWN: "UNKNOWN",
}


@lru_cache(maxsize=256)
def get_country_info(country_code: str) -> Optional[dict]:
    try:
        country = pycountry.countries.get(alpha_2=country_code.upper())
        if not country:
            return None
        return {
            "name": country.name,
            "alpha_2": country.alpha_2,
            "alpha_3": getattr(country, 'alpha_3', None),
            "numeric": getattr(country, 'numeric', None),
        }
    except Exception as e:
        logger.error(f"Error fetching country info for {country_code}: {e}")
        return None


def get_number_type_name(number_type: int) -> str:
    return _NUMBER_TYPE_MAPPING.get(number_type, "UNKNOWN")


def validate_api_token(x_api_token: Optional[str]) -> bool:
    if not x_api_token:
        return False
    return x_api_token == API_TOKEN


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="Phone Number Lookup API",
        version="1.0.0",
        api_token_configured=(API_TOKEN != "dev-token-change-in-production")
    )


@app.get("/lookup", response_model=PhoneNumberInfo)
async def lookup_phone_number(
    phone: str = Query(..., min_length=1),
    country: Optional[str] = Query(None, max_length=2),
    x_api_token: str = Header(...)
) -> PhoneNumberInfo:
    if not validate_api_token(x_api_token):
        logger.warning("Unauthorized access attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token"
        )

    if not phone.startswith('+') and not country:
        phone = '+' + phone

    try:
        parsed_number = phonenumbers.parse(phone, country)
    except NumberParseException as e:
        logger.error(f"Phone number parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    except Exception as e:
        logger.error(f"Error parsing phone number: {str(e)}")
        raise HTTPException(status_code=400, detail="Error parsing phone number")

    country_code = phonenumbers.region_code_for_number(parsed_number)
    country_info = get_country_info(country_code)

    if not country_info:
        raise HTTPException(status_code=404, detail=f"Country not found: {country_code}")

    number_type = phonenumbers.number_type(parsed_number)
    number_type_name = get_number_type_name(number_type)
    is_valid = phonenumbers.is_valid_number(parsed_number)
    is_possible = phonenumbers.is_possible_number(parsed_number)
    formatted_e164 = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    formatted_national = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL)

    logger.info(f"Successfully looked up phone number from country: {country_code}")

    return PhoneNumberInfo(
        phone_number=str(parsed_number),
        country_code=country_code,
        country_name=country_info["name"],
        country_region=None,
        number_type=number_type_name,
        is_valid=is_valid,
        is_possible=is_possible,
        formatted_e164=formatted_e164,
        formatted_national=formatted_national,
        timezone=None
    )


@app.get("/validate", response_model=ValidationResult)
async def validate_phone_number(
    phone: str = Query(..., min_length=1),
    country: Optional[str] = Query(None, max_length=2),
    x_api_token: str = Header(...)
) -> ValidationResult:
    if not validate_api_token(x_api_token):
        logger.warning("Unauthorized access attempt to /validate")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token"
        )

    if not phone.startswith('+') and not country:
        phone = '+' + phone

    try:
        parsed_number = phonenumbers.parse(phone, country)
        is_valid = phonenumbers.is_valid_number(parsed_number)
        is_possible = phonenumbers.is_possible_number(parsed_number)
        detected_country = phonenumbers.region_code_for_number(parsed_number)

        logger.info(f"Successfully validated phone number from country: {detected_country}")

        return ValidationResult(
            phone=phone,
            is_valid=is_valid,
            is_possible=is_possible,
            country_code=detected_country,
            error=None
        )
    except NumberParseException as e:
        logger.warning(f"Phone number validation error: {str(e)}")
        return ValidationResult(
            phone=phone,
            is_valid=False,
            is_possible=False,
            country_code=None,
            error=str(e)
        )


@app.get("/supported-countries", response_model=CountriesResponse)
async def get_supported_countries(x_api_token: str = Header(...)) -> CountriesResponse:
    if not validate_api_token(x_api_token):
        logger.warning("Unauthorized access attempt to /supported-countries")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token"
        )

    countries = []
    for country in pycountry.countries:
        countries.append(
            CountryInfo(
                name=country.name,
                alpha_2=country.alpha_2,
                alpha_3=country.alpha_3,
                numeric=country.numeric
            )
        )

    countries_sorted = sorted(countries, key=lambda x: x.name)
    logger.info(f"Retrieved list of {len(countries_sorted)} supported countries")

    return CountriesResponse(
        total=len(countries_sorted),
        countries=countries_sorted
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 4))
    log_level = os.getenv("LOG_LEVEL", "info")

    logger.info(f"Starting Phone Number Lookup API on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        reload=False,
        access_log=True
    )
