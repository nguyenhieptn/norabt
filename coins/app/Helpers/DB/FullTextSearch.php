<?php

namespace App\Helpers\DB;

class FullTextSearch
{
    /**
     * Replaces spaces with full text search wildcards
     *
     * @param string $term
     * @return string
     */
    public static function fullTextWildcards($term)
    {
        // removing symbols used by MySQL
        $reservedSymbols = ['-', '+', '<', '>', '@', '(', ')', '~'];
        $term = str_replace($reservedSymbols, '', $term);
 
        $words = explode(' ', $term);
 
        foreach ($words as $key => $word) {
            /*
             * applying + operator (required word) only big words
             * because smaller ones are not indexed by mysql
             */
            if (strlen($word) >= 3) {
                $words[$key] = '+' . $word . '*';
            }
        }
 
        $searchTerm = implode(' ', $words);
 
        return $searchTerm;
    } 
 
    /**
     * Scope a query that matches a full text search of term.
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param string $term
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public static function fullTextSearch($query, $columns, $term, $boolean = false)
    {
        $columns = implode(',', $columns);
        if($boolean){
            $query->whereRaw("MATCH ({$columns}) AGAINST (? IN BOOLEAN MODE)", self::fullTextWildcards($term));
        }else{
            $query->whereRaw("MATCH ({$columns}) AGAINST (?)", $term);
        }
        
 
        return $query;
    }
}