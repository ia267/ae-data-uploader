"""
Index generation for byte-offset selective downloading.

This module creates JSON indices for various file formats to enable
selective downloading using HTTP Range requests.
"""

import json
import struct
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)


class IndexGenerator:
    """Generate byte-offset indices for various file formats."""
    
    @staticmethod
    def generate(file_path: Union[str, Path], 
                 file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate byte-offset index for a file.
        
        Args:
            file_path: Path to the file
            file_type: Optional file type hint ('hdf5', 'csv', 'netcdf', 'binary', etc.)
                      If not provided, will be inferred from extension
                      
        Returns:
            Dictionary containing the byte-offset index
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Infer file type from extension if not provided
        if file_type is None:
            file_type = IndexGenerator._infer_file_type(file_path)
        
        # Route to appropriate handler
        if file_type == 'hdf5':
            return IndexGenerator._generate_hdf5_index(file_path)
        elif file_type == 'csv':
            return IndexGenerator._generate_csv_index(file_path)
        elif file_type == 'netcdf':
            return IndexGenerator._generate_netcdf_index(file_path)
        elif file_type == 'binary':
            return IndexGenerator._generate_binary_index(file_path)
        else:
            # Generic index with basic file info
            return IndexGenerator._generate_generic_index(file_path)
    
    @staticmethod
    def _infer_file_type(file_path: Path) -> str:
        """Infer file type from extension."""
        ext = file_path.suffix.lower()
        
        type_map = {
            '.h5': 'hdf5',
            '.hdf5': 'hdf5',
            '.hdf': 'hdf5',
            '.csv': 'csv',
            '.nc': 'netcdf',
            '.nc4': 'netcdf',
            '.netcdf': 'netcdf',
            '.bin': 'binary',
            '.dat': 'binary',
        }
        
        return type_map.get(ext, 'generic')
    
    @staticmethod
    def _generate_hdf5_index(file_path: Path) -> Dict[str, Any]:
        """Generate index for HDF5 files."""
        try:
            import h5py
        except ImportError:
            raise ImportError(
                "h5py is required for HDF5 index generation. "
                "Install with: pip install h5py"
            )
        
        index = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": "hdf5",
            "datasets": {}
        }
        
        # Open HDF5 file and extract dataset information
        # Use driver='core' to load minimal structure into memory
        with h5py.File(file_path, 'r', driver='core', 
                       backing_store=False, rdcc_nbytes=1024*1024) as f:
            
            def visit_datasets(name, obj):
                if isinstance(obj, h5py.Dataset):
                    # Get dataset information
                    ds_info = {
                        "shape": [int(s) for s in obj.shape],
                        "dtype": str(obj.dtype),
                        "size_bytes": int(obj.nbytes),
                    }
                    
                    # Try to get byte offset (requires low-level API)
                    try:
                        # Get dataset creation property list
                        dcpl = obj.id.get_create_plist()
                        layout = dcpl.get_layout()
                        
                        if layout == h5py.h5d.CONTIGUOUS:
                            # For contiguous storage, we can get the offset
                            offset = obj.id.get_offset()
                            if offset is not None:
                                ds_info["byte_offset"] = int(offset)
                    except:
                        # If we can't get offset, that's okay
                        pass
                    
                    # Add attributes (convert numpy types to Python types)
                    if obj.attrs:
                        attrs = {}
                        for key, value in obj.attrs.items():
                            if isinstance(value, (np.integer, np.int64)):
                                attrs[key] = int(value)
                            elif isinstance(value, (np.floating, np.float64)):
                                attrs[key] = float(value)
                            elif isinstance(value, np.ndarray):
                                attrs[key] = value.tolist()
                            elif isinstance(value, np.bool_):
                                attrs[key] = bool(value)
                            elif isinstance(value, bytes):
                                attrs[key] = value.decode('utf-8', errors='ignore')
                            else:
                                attrs[key] = value
                        ds_info["attributes"] = attrs
                    
                    index["datasets"][name] = ds_info
            
            # Visit all datasets
            f.visititems(visit_datasets)
            
            # Add file-level attributes (convert numpy types to Python types)
            if f.attrs:
                file_attrs = {}
                for key, value in f.attrs.items():
                    if isinstance(value, (np.integer, np.int64)):
                        file_attrs[key] = int(value)
                    elif isinstance(value, (np.floating, np.float64)):
                        file_attrs[key] = float(value)
                    elif isinstance(value, np.ndarray):
                        file_attrs[key] = value.tolist()
                    elif isinstance(value, np.bool_):
                        file_attrs[key] = bool(value)
                    elif isinstance(value, bytes):
                        file_attrs[key] = value.decode('utf-8', errors='ignore')
                    else:
                        file_attrs[key] = value
                index["file_attributes"] = file_attrs
        
        return index
    
    @staticmethod
    def _generate_csv_index(file_path: Path, 
                           chunk_size: int = 100000,
                           max_chunks: int = 100) -> Dict[str, Any]:
        """
        Generate index for CSV files.
        
        Creates line-based chunks for selective access.
        """
        index = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": "csv",
            "chunks": {}
        }
        
        with open(file_path, 'rb') as f:
            # Read header
            first_line = f.readline()
            header_bytes = len(first_line)
            
            try:
                header = first_line.decode('utf-8').strip()
                index["header"] = {
                    "content": header,
                    "byte_range": [0, header_bytes - 1]
                }
                
                # Try to detect columns
                if ',' in header:
                    index["columns"] = [col.strip() for col in header.split(',')]
            except:
                index["header"] = {
                    "byte_range": [0, header_bytes - 1]
                }
            
            # Create chunks
            chunk_id = 0
            line_num = 1
            byte_offset = header_bytes
            
            while chunk_id < max_chunks:
                chunk_start_line = line_num
                chunk_start_byte = byte_offset
                
                # Read chunk_size lines
                lines_read = 0
                while lines_read < chunk_size:
                    line = f.readline()
                    if not line:
                        break
                    byte_offset += len(line)
                    lines_read += 1
                    line_num += 1
                
                if lines_read == 0:
                    break
                
                # Record chunk
                index["chunks"][f"chunk_{chunk_id}"] = {
                    "line_range": [chunk_start_line, line_num - 1],
                    "byte_range": [chunk_start_byte, byte_offset - 1],
                    "num_lines": lines_read
                }
                
                chunk_id += 1
        
        index["total_chunks"] = chunk_id
        
        return index
    
    @staticmethod
    def _generate_netcdf_index(file_path: Path) -> Dict[str, Any]:
        """Generate index for NetCDF files."""
        try:
            import netCDF4 as nc
        except ImportError:
            raise ImportError(
                "netCDF4 is required for NetCDF index generation. "
                "Install with: pip install netCDF4"
            )
        
        index = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": "netcdf",
            "variables": {},
            "dimensions": {}
        }
        
        with nc.Dataset(file_path, 'r') as ds:
            # Add dimensions
            for dim_name, dim in ds.dimensions.items():
                index["dimensions"][dim_name] = {
                    "size": len(dim),
                    "unlimited": dim.isunlimited()
                }
            
            # Add variables
            for var_name, var in ds.variables.items():
                var_info = {
                    "dimensions": list(var.dimensions),
                    "shape": list(var.shape),
                    "dtype": str(var.dtype),
                    "size_bytes": var.size * var.dtype.itemsize
                }
                
                # Add attributes
                if var.ncattrs():
                    var_info["attributes"] = {
                        attr: var.getncattr(attr) for attr in var.ncattrs()
                    }
                
                index["variables"][var_name] = var_info
            
            # Add global attributes
            if ds.ncattrs():
                index["global_attributes"] = {
                    attr: ds.getncattr(attr) for attr in ds.ncattrs()
                }
        
        return index
    
    @staticmethod
    def _generate_binary_index(file_path: Path,
                               record_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate index for binary files.
        
        If record_size is provided, creates record-based index.
        """
        index = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": "binary"
        }
        
        if record_size:
            # Create record-based index
            file_size = file_path.stat().st_size
            num_records = file_size // record_size
            
            index["record_size"] = record_size
            index["num_records"] = num_records
            index["records"] = {}
            
            for i in range(min(num_records, 1000)):  # Limit to 1000 entries
                index["records"][f"record_{i}"] = {
                    "byte_range": [i * record_size, (i + 1) * record_size - 1]
                }
        else:
            # Just basic file info
            index["note"] = "Binary file without structure information. " \
                           "Provide record_size for detailed index."
        
        return index
    
    @staticmethod
    def _generate_generic_index(file_path: Path) -> Dict[str, Any]:
        """Generate basic index for unknown file types."""
        return {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_type": "generic",
            "note": "Generic index. Install format-specific libraries for detailed indices."
        }


class MultiFileIndexGenerator:
    """Generate master index for multiple files."""
    
    @staticmethod
    def generate_master_index(directory: Union[str, Path],
                             pattern: Optional[str] = None,
                             strategy: str = "master") -> Dict[str, Any]:
        """
        Generate master index for multiple files in a directory.
        
        Args:
            directory: Path to directory containing files
            pattern: Glob pattern to filter files (e.g., "*.h5", "sim_*.nc")
            strategy: Index strategy - "master", "hierarchical", or "individual"
            
        Returns:
            Master index dictionary
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Find files matching pattern
        if pattern:
            files = sorted(directory.glob(pattern))
        else:
            # Find all non-hidden files
            files = sorted([f for f in directory.iterdir() 
                          if f.is_file() and not f.name.startswith('.')])
        
        if not files:
            raise ValueError(f"No files found in {directory} matching pattern: {pattern}")
        
        if strategy == "master":
            return MultiFileIndexGenerator._generate_master(directory, files)
        elif strategy == "hierarchical":
            return MultiFileIndexGenerator._generate_hierarchical(directory, files)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    @staticmethod
    def _generate_master(directory: Path, files: List[Path]) -> Dict[str, Any]:
        """Generate single master index for all files."""
        master_index = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "index_type": "master",
            "directory": directory.name,
            "total_files": len(files),
            "total_size": sum(f.stat().st_size for f in files),
            "files": {}
        }
        
        # Group files by type
        file_groups = {}
        for file_path in files:
            file_type = IndexGenerator._infer_file_type(file_path)
            if file_type not in file_groups:
                file_groups[file_type] = []
            file_groups[file_type].append(file_path)
        
        # Generate indices for each group
        for file_type, group_files in file_groups.items():
            if len(group_files) == 1:
                # Single file - include full index
                file_path = group_files[0]
                master_index["files"][file_path.name] = IndexGenerator.generate(file_path)
            else:
                # Multiple files - check if they have common structure
                master_index["files"][file_type + "_group"] = {
                    "file_count": len(group_files),
                    "file_list": [f.name for f in group_files],
                    "note": f"{len(group_files)} {file_type} files"
                }
                
                # Generate index for first file as template
                if file_type in ['hdf5', 'netcdf', 'csv']:
                    first_file = group_files[0]
                    master_index["files"][file_type + "_structure"] = \
                        IndexGenerator.generate(first_file)
        
        return master_index
    
    @staticmethod
    def _generate_hierarchical(directory: Path, files: List[Path]) -> Dict[str, Any]:
        """Generate hierarchical index structure."""
        # Create master catalog
        catalog = {
            "version": "1.0",
            "created": datetime.utcnow().isoformat() + "Z",
            "index_type": "hierarchical_catalog",
            "directory": directory.name,
            "total_files": len(files),
            "file_groups": {}
        }
        
        # Group files by type
        file_groups = {}
        for file_path in files:
            file_type = IndexGenerator._infer_file_type(file_path)
            if file_type not in file_groups:
                file_groups[file_type] = []
            file_groups[file_type].append(file_path)
        
        # Create group entries in catalog
        for file_type, group_files in file_groups.items():
            catalog["file_groups"][file_type] = {
                "file_count": len(group_files),
                "detailed_index": f"{directory.name}_{file_type}_index.json",
                "file_list": [f.name for f in group_files]
            }
        
        return catalog


def save_index(index: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """
    Save index to JSON file.
    
    Args:
        index: Index dictionary
        output_path: Path to save the index
    """
    output_path = Path(output_path)
    
    with open(output_path, 'w') as f:
        json.dump(index, f, indent=2, cls=NumpyEncoder)
