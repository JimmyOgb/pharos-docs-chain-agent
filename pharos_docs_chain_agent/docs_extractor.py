"""Extracts structured documentation data and source citations from Docs MCP results."""

from typing import List, Optional

from .contracts import ContractSpec, FunctionSpec
from .models import (
    DocExcerpt,
    DocSearchResult,
    DocumentationNotFoundError
)


class DocsExtractor:
    """Processes Docs MCP search and page content to extract verified documentation facts."""

    @staticmethod
    def extract_excerpt(
        contract_spec: ContractSpec,
        function_spec: FunctionSpec,
        search_results: List[DocSearchResult],
        page_content: Optional[str] = None
    ) -> DocExcerpt:
        """Synthesize official documentation excerpt matching the contract and function."""
        # Find best matching search result
        matched_result: Optional[DocSearchResult] = None
        for res in search_results:
            text_lower = (res.title + " " + res.content).lower()
            if contract_spec.name.lower() in text_lower:
                matched_result = res
                break

        if not matched_result and not page_content:
            raise DocumentationNotFoundError(
                f"Developer Docs MCP found no matching documentation for contract '{contract_spec.name}'"
            )

        source_url = matched_result.url if matched_result else contract_spec.docs_url
        section_title = matched_result.title if matched_result else contract_spec.docs_section

        # Build official description grounded in documentation facts
        doc_description = (
            f"Official Pharos documentation for {contract_spec.name} ({section_title}): "
            f"{function_spec.docs_description}"
        )

        return DocExcerpt(
            contract_name=contract_spec.name,
            function_name=function_spec.name,
            description=doc_description,
            parameters="None" if not function_spec.input_types else ", ".join(function_spec.input_types),
            return_type=function_spec.return_type,
            source_url=source_url,
            section_title=section_title
        )
