"""Loader for ronten (issue points) files with structured parsing."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from config.settings import Settings, get_settings


@dataclass
class RontenItem:
    """A single discussion point (ronten) from legislative council."""
    id: str  # e.g., "functional_equivalence"
    title: str  # e.g., "機能的同等性"
    description: str  # Detailed description
    keywords: List[str] = field(default_factory=list)  # Keywords for matching
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
        }


# Pre-defined ronten items for bill-of-lading (電子船荷証券)
BILL_OF_LADING_RONTEN: List[RontenItem] = [
    RontenItem(
        id="functional_equivalence",
        title="機能的同等性",
        description="紙の船荷証券が持つ法的効力と商慣習上の機能をデジタル環境で再現する「機能的同等性」の達成",
        keywords=["機能的同等性", "MLETR", "UNCITRAL", "モデル法", "同等", "再現", "デジタル化", "電子化のメリット"],
    ),
    RontenItem(
        id="control_concept",
        title="「支配」概念の具体化",
        description="デジタル空間における「所持」を「支配」として法的に定義し、客観的かつ技術的中立性を保った形で具体化する",
        keywords=["支配", "コントロール", "control", "所持", "占有", "排他的", "情報処理システム", "技術的中立性"],
    ),
    RontenItem(
        id="system_provider_status",
        title="情報システム提供者の法的地位",
        description="システム提供者を法的主体として規律に組み込むべきか否か、認許可制などの規制への懸念",
        keywords=["システム提供者", "プロバイダー", "プラットフォーム", "規制", "認許可", "中央集権", "分散型", "ブロックチェーン"],
    ),
    RontenItem(
        id="enforcement",
        title="強制執行の実効性確保",
        description="物理的な占有が不可能なeB/Lをいかに差し押さえるか、甲案・丙案・丁案の検討",
        keywords=["強制執行", "差押え", "差し押さえ", "執行", "甲案", "丙案", "丁案", "債権者", "担保"],
    ),
    RontenItem(
        id="ebl_types",
        title="電子船荷証券の類型（A案/B案/C案）",
        description="A案（シンプル化）、B案（現状維持・4類型維持）、C案（ハイブリッド）の比較検討。B案が有力",
        keywords=["A案", "B案", "C案", "類型", "指図式", "記名式", "無記名", "bearer", "譲渡禁止"],
    ),
    RontenItem(
        id="electronic_endorsement",
        title="電子裏書のメカニズム",
        description="紙の裏書を再現する「電子裏書」の導入、電子署名要件、白地式電子裏書の規定",
        keywords=["電子裏書", "裏書", "endorsement", "電子署名", "白地式", "譲渡", "被裏書人"],
    ),
    RontenItem(
        id="legal_effects",
        title="法的効力の同等性",
        description="物権的効力、権利推定効・善意取得、受戻証券性の3つの核心的権能の確保",
        keywords=["物権的効力", "権利推定", "善意取得", "受戻証券性", "担保", "貿易金融", "引渡し"],
    ),
    RontenItem(
        id="conversion",
        title="紙と電子の相互転換",
        description="eB/Lから紙への転換を権利とするか合意によるか。当事者間の合意に委ねる方向",
        keywords=["転換", "conversion", "紙から電子", "電子から紙", "相互運用", "互換性"],
    ),
    RontenItem(
        id="system_failure",
        title="システム障害時の対応",
        description="システム障害による記録の喪失時の対応。公示催告・除権決定の手続は不要とする方向",
        keywords=["システム障害", "喪失", "バックアップ", "復旧", "公示催告", "除権決定", "紛失", "データ"],
    ),
]


class RontenLoader:
    """Loads ronten (issue points) context from files with structured parsing."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize loader."""
        self.settings = settings or get_settings()
        self._ronten_items_cache: Dict[str, List[RontenItem]] = {}
        
    def load_ronten_content(self, survey_slug: str) -> str:
        """Load ronten content for a specific survey slug.
        
        Searches for ronten files matching the pattern:
        - {survey_slug}_ronten.txt
        - {survey_slug}_*_ronten.txt
        
        Only loads files that start with the survey slug to avoid loading
        unrelated ronten files.
        
        Args:
            survey_slug: The slug of the survey (e.g. 'bill-of-lading')
            
        Returns:
            Combined content of all matching ronten files or empty string if not found
        """
        data_dir = Path(self.settings.data_dir)
        
        if not data_dir.exists():
            return ""
        
        # Find all ronten files matching the survey slug pattern
        # Pattern: {survey_slug}_*_ronten.txt or {survey_slug}_ronten.txt
        matching_files = []
        for file_path in data_dir.glob(f"{survey_slug}*_ronten.txt"):
            # Ensure the file starts with the exact survey slug
            # (avoid partial matches like "bill" matching "bill-of-lading")
            filename = file_path.name
            if filename.startswith(f"{survey_slug}_"):
                matching_files.append(file_path)
        
        if not matching_files:
            # Fallback to explicit mapping for backward compatibility
            filename = self.settings.ronten_file_mapping.get(survey_slug)
            if filename:
                file_path = data_dir / filename
                if file_path.exists():
                    matching_files = [file_path]
        
        if not matching_files:
            return ""
        
        # Load and combine all matching files
        contents = []
        for file_path in sorted(matching_files):
            try:
                content = file_path.read_text(encoding='utf-8')
                if content.strip():
                    contents.append(f"# Source: {file_path.name}\n\n{content}")
            except Exception as e:
                print(f"Error loading ronten file {file_path}: {e}")
        
        return "\n\n---\n\n".join(contents)
    
    def get_ronten_items(self, survey_slug: str) -> List[RontenItem]:
        """Get structured ronten items for a survey slug.
        
        Args:
            survey_slug: The slug of the survey
            
        Returns:
            List of RontenItem objects
        """
        if survey_slug in self._ronten_items_cache:
            return self._ronten_items_cache[survey_slug]
        
        # Currently only bill-of-lading has predefined ronten items
        if survey_slug == "bill-of-lading":
            items = BILL_OF_LADING_RONTEN
        else:
            items = []
        
        self._ronten_items_cache[survey_slug] = items
        return items
    
    def get_ronten_summary(self, survey_slug: str) -> str:
        """Get a summary of all ronten items as a formatted string.
        
        Args:
            survey_slug: The slug of the survey
            
        Returns:
            Formatted string with all ronten items
        """
        items = self.get_ronten_items(survey_slug)
        if not items:
            return ""
        
        lines = ["## 法制審議会での主要論点\n"]
        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. {item.title}")
            lines.append(f"{item.description}\n")
        
        return "\n".join(lines)
    
    def get_ronten_for_prompt(self, survey_slug: str) -> str:
        """Get ronten items formatted for LLM prompts.
        
        Args:
            survey_slug: The slug of the survey
            
        Returns:
            Formatted string for LLM prompts with numbered list
        """
        items = self.get_ronten_items(survey_slug)
        if not items:
            return "（論点情報なし）"
        
        lines = []
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. **{item.title}**: {item.description}")
        
        return "\n".join(lines)




